"""Kết nối DB read-only cho NL2SQL Agent.

Dù connection được mở bằng tài khoản gì (Windows Auth mặc định, hoặc SQL
login qua DB_READONLY_USER/PASSWORD trong .env nếu môi trường đã bật SQL
Server mixed-mode auth), mọi câu SELECT đã qua sql_validator đều được chạy
dưới danh nghĩa user hạn chế `nl2sql_readonly` (EXECUTE AS - xem
execute_select()) - user này chỉ được GRANT SELECT trên vw_game_sales_full,
KHÔNG có quyền gì trên 8 bảng gốc (sql/hoang/10_readonly_login.sql, tạo bằng
CREATE USER ... WITHOUT LOGIN nên không cần mixed-mode auth). Đây là lớp
phòng thủ ở tầng DB, độc lập với whitelist bảng ở app-layer
(sql_validator.py) - nếu lớp app-layer có lỗ hổng bypass, DB vẫn tự chặn.

Tái sử dụng 1 connection cho cả tiến trình thay vì mở/đóng mỗi câu hỏi - mở
connection mới tới named instance (qua SQL Browser) có thể mất vài chục giây
mỗi lần và không ổn định (đo được qua trang /admin), nên chỉ mở lại khi
connection cũ đã chết.

MARS_Connection=yes + autocommit=True: connection tái sử dụng lâu dài dễ dính
lỗi "Query timeout expired" ngẫu nhiên nếu thiếu MARS (cursor health-check
"SELECT 1" chưa được đóng/fetch hết trước khi cursor tiếp theo execute() -
không có MARS thì driver phải chờ, gây timeout dù chính câu SQL đó chạy trực
tiếp bằng sqlcmd chỉ mất vài chục ms). autocommit=True tránh transaction ngầm
tích luỹ qua thời gian sống dài của connection (an toàn vì chỉ SELECT).

webapp.py chạy Flask với threaded=True (nhiều request /ask có thể chạy song
song), nhưng 1 connection pyodbc dùng chung KHÔNG an toàn nếu nhiều thread
gọi execute() đồng thời trên cùng 1 connection - nên execute_select() khoá
(_lock) cho toàn bộ thao tác truy vấn, không chỉ lúc lấy connection. Vì các
câu query đã nhanh (sau khi có index, xem 09_indexes.sql) nên khoá tuần tự ở
đây không phải là điểm nghẽn hiệu năng.
"""
import threading
import time

import pyodbc

from .config import CONFIG

_conn = None
_lock = threading.RLock()  # reentrant: execute_select() giu lock roi goi _get_connection()

_FRESHNESS_CACHE_TTL_SECONDS = 300
_freshness_cache = None
_freshness_cache_at = 0.0


def _connection_string() -> str:
    base = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={CONFIG.db_server};DATABASE={CONFIG.db_name};"
        # MARS: cho phep nhieu cursor/statement tren cung 1 connection khong
        # bi ket nhau - thieu dong nay la nguyen nhan that cua timeout ngau
        # nhien (cursor "SELECT 1" o health-check khong duoc dong truoc khi
        # cursor tiep theo execute(), driver phai cho ma khong co MARS).
        "MARS_Connection=yes;"
    )
    if CONFIG.db_readonly_user:
        return base + (
            f"UID={CONFIG.db_readonly_user};PWD={CONFIG.db_readonly_password};"
        )
    return base + "Trusted_Connection=yes;"


def _new_connection() -> pyodbc.Connection:
    conn = pyodbc.connect(
        _connection_string(), timeout=CONFIG.query_timeout_seconds, autocommit=True
    )
    conn.timeout = CONFIG.query_timeout_seconds  # gioi han thoi gian chay 1 cau query
    return conn


def _get_connection() -> pyodbc.Connection:
    global _conn
    with _lock:
        if _conn is not None:
            try:
                cur = _conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchall()
                cur.close()
                return _conn
            except Exception:
                try:
                    _conn.close()
                except Exception:
                    pass
                _conn = None
        _conn = _new_connection()
        return _conn


def execute_select(sql: str):
    """Chạy 1 câu SELECT (đã qua sql_validator) và trả về (columns, rows).

    Khoá toàn bộ thao tác (không chỉ lúc lấy connection) vì connection dùng
    chung không an toàn cho nhiều thread gọi execute() đồng thời.

    Bọc câu query trong EXECUTE AS USER = 'nl2sql_readonly' ... REVERT (defense
    in depth ở tầng DB - xem sql/hoang/10_readonly_login.sql): user này chỉ
    được GRANT SELECT trên vw_game_sales_full, không có quyền gì trên 8 bảng
    gốc, nên nếu sql_validator.py có lỗ hổng bypass nào đó thì DB vẫn tự chặn.
    REVERT luôn chạy trong finally để connection tái sử dụng không bị "kẹt"
    dưới quyền hạn chế cho lần gọi sau.
    """
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("EXECUTE AS USER = 'nl2sql_readonly'")
        try:
            cursor.execute(sql)
            columns = [c[0] for c in cursor.description]
            rows = [tuple(row) for row in cursor.fetchall()]
            return columns, rows
        finally:
            cursor.execute("REVERT")


def get_data_freshness() -> dict:
    """3 tín hiệu tách bạch rõ ràng (dùng cho /admin và trang chat) - trước đây
    gộp chung thành "freshness" là sai bản chất, đã sửa theo đúng thuật ngữ
    data engineering:

    - last_data_update: FRESHNESS THẬT (ingestion/update lag) - lấy từ cột
      region_sales.updated_at (sql/hoang/11_freshness_columns.sql), tự động
      cập nhật bằng trigger trg_region_sales_updated mỗi khi có UPDATE thật -
      chính xác 100%, không còn là proxy suy luận như STATS_DATE trước đây
      (STATS_DATE chỉ phản ánh lần optimizer tự update thống kê, có ngưỡng
      ~20% số dòng thay đổi mới trigger, hoặc nhảy giả khi ai đó chạy UPDATE
      STATISTICS thủ công dù không ai ghi dữ liệu - không đáng tin để khẳng
      định "dữ liệu có mới không").
    - content_coverage_year: CONTENT COVERAGE (không phải freshness) - năm
      phát hành mới nhất có trong dữ liệu, trả lời "nội dung phủ tới đâu",
      không nói lên gì về việc hệ thống có vừa đồng bộ dữ liệu hay không.
    - total_rows: COMPLETENESS/INTEGRITY check - tổng số dòng doanh số, đối
      chiếu xem dữ liệu có bị thiếu/mất so với lần trước không.

    Cache trong tiến trình (TTL 5 phút): các câu SELECT dưới đều là aggregate
    đơn giản trên 1 bảng (không join qua vw_game_sales_full - "Bug thật thứ
    3/4", NL2SQL_ARCHITECTURE.md mục 7) nên đã rất nhanh, nhưng vẫn cache vì
    /admin tự refresh mỗi 45s, gọi lại y hệt câu này liên tục nếu không cache.
    """
    global _freshness_cache, _freshness_cache_at
    with _lock:
        if _freshness_cache is not None and (time.time() - _freshness_cache_at) < _FRESHNESS_CACHE_TTL_SECONDS:
            return _freshness_cache
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT (SELECT MAX(release_year) FROM game_platform), "
            "(SELECT COUNT(*) FROM region_sales), "
            "(SELECT MAX(updated_at) FROM region_sales)"
        )
        content_coverage_year, total_rows, last_data_update = cur.fetchone()

        _freshness_cache = {
            "content_coverage_year": content_coverage_year,
            "total_rows": total_rows,
            "last_data_update": last_data_update,
        }
        _freshness_cache_at = time.time()
        return _freshness_cache
