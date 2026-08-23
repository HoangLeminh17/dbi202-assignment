"""Kết nối DB read-only cho NL2SQL Agent.

Sản xuất thật PHẢI trỏ vào 1 SQL Server login chỉ có quyền SELECT trên
vw_game_sales_full (GRANT SELECT ON vw_game_sales_full TO nl2sql_readonly;
KHÔNG cấp quyền trên bảng gốc) - không bao giờ dùng sa/admin. Bên dưới hỗ trợ
cả Windows Authentication (chỉ cho môi trường local/dev) khi không có
DB_READONLY_USER trong .env.

Tái sử dụng 1 connection cho cả tiến trình thay vì mở/đóng mỗi câu hỏi - mở
connection mới tới named instance (qua SQL Browser) có thể mất vài chục giây
mỗi lần và không ổn định (đo được qua trang /admin), nên chỉ mở lại khi
connection cũ đã chết.

webapp.py chạy Flask với threaded=True (nhiều request /ask có thể chạy song
song), nhưng 1 connection pyodbc dùng chung KHÔNG an toàn nếu nhiều thread
gọi execute() đồng thời trên cùng 1 connection - nên execute_select() khoá
(_lock) cho toàn bộ thao tác truy vấn, không chỉ lúc lấy connection. Vì các
câu query đã nhanh (sau khi có index, xem 09_indexes.sql) nên khoá tuần tự ở
đây không phải là điểm nghẽn hiệu năng.
"""
import threading

import pyodbc

from .config import CONFIG

_conn = None
_lock = threading.RLock()  # reentrant: execute_select() giu lock roi goi _get_connection()


def _connection_string() -> str:
    base = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={CONFIG.db_server};DATABASE={CONFIG.db_name};"
    )
    if CONFIG.db_readonly_user:
        return base + (
            f"UID={CONFIG.db_readonly_user};PWD={CONFIG.db_readonly_password};"
        )
    return base + "Trusted_Connection=yes;"


def _new_connection() -> pyodbc.Connection:
    conn = pyodbc.connect(_connection_string(), timeout=CONFIG.query_timeout_seconds)
    conn.timeout = CONFIG.query_timeout_seconds  # gioi han thoi gian chay 1 cau query
    return conn


def _get_connection() -> pyodbc.Connection:
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.cursor().execute("SELECT 1")
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
    """
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        rows = [tuple(row) for row in cursor.fetchall()]
        return columns, rows
