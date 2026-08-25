"""Lưu log từng request của NL2SQL Agent vào SQLite, phục vụ trang /admin.

Mỗi lần agent.ask() chạy xong (dù thành công hay bị guardrail/validator chặn)
đều ghi 1 dòng vào bảng request_logs - đủ để admin xem lại toàn bộ luồng xử
lý phía user: câu hỏi, SQL đã sinh, có bị chặn không (và chặn ở bước nào),
số dòng kết quả, câu trả lời, thời gian từng bước.
"""
import os
import sqlite3
from pathlib import Path

# Cho phep override qua LOGS_DB_PATH (vd trong Docker, mount volume rieng
# ngoai thu muc code de log song sot qua cac lan restart container).
DB_PATH = Path(os.getenv("LOGS_DB_PATH") or (Path(__file__).parent / "logs.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    question TEXT NOT NULL,
    blocked INTEGER NOT NULL,
    block_stage TEXT,
    reason TEXT,
    raw_sql TEXT,
    safe_sql TEXT,
    row_count INTEGER,
    answer TEXT,
    llm_provider TEXT,
    llm_model TEXT,
    ms_generate_sql INTEGER,
    ms_db_exec INTEGER,
    ms_explain INTEGER,
    ms_total INTEGER
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    # feedback + cac cot token duoc them sau ban dau (CREATE TABLE IF NOT
    # EXISTS khong tu them cot moi vao bang cu da ton tai) - migrate bang
    # ALTER, bo qua loi neu cot da co san.
    for ddl in (
        "ALTER TABLE request_logs ADD COLUMN feedback TEXT",
        "ALTER TABLE request_logs ADD COLUMN input_tokens INTEGER",
        "ALTER TABLE request_logs ADD COLUMN output_tokens INTEGER",
        "ALTER TABLE request_logs ADD COLUMN cache_read_tokens INTEGER",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass
    return conn


def record(**fields) -> int:
    conn = _connect()
    try:
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        cur = conn.execute(
            f"INSERT INTO request_logs ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def set_feedback(request_id: int, feedback: str | None) -> bool:
    """feedback: 'up'/'down' de danh gia, None de bo danh gia (bam lai nut da chon).
    Tra ve False neu request_id khong ton tai.
    """
    if feedback not in ("up", "down", None):
        raise ValueError(f"feedback không hợp lệ: {feedback}")
    conn = _connect()
    try:
        cur = conn.execute(
            "UPDATE request_logs SET feedback = ? WHERE id = ?", (feedback, request_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def fetch_feedback_stats() -> dict:
    conn = _connect()
    try:
        up = conn.execute(
            "SELECT COUNT(*) FROM request_logs WHERE feedback = 'up'"
        ).fetchone()[0]
        down = conn.execute(
            "SELECT COUNT(*) FROM request_logs WHERE feedback = 'down'"
        ).fetchone()[0]
        return {"up": up, "down": down}
    finally:
        conn.close()


def fetch_recent(
    limit: int = 200,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    year: str = None,
    feedback: str = None,
) -> list:
    """Mọi điều kiện lọc kết hợp kiểu AND (thu hẹp dần), không phải OR.

    status: None/"" = tất cả; "ok" = thành công; "blocked" = bị chặn theo
    thiết kế (guardrail/validator); "error" = lỗi hạ tầng (service_error) -
    cùng cách nhóm 3 trạng thái với donut chart ở trên (_build_donut).
    date_from/date_to: chuỗi "YYYY-MM-DD" - so sánh trực tiếp theo prefix của
    created_at (ISO 8601 nên so sánh chuỗi vẫn đúng thứ tự thời gian, không
    cần parse datetime).
    year: chuỗi "YYYY" - loc nhanh nguyên 1 năm (tuong duong date_from=Y-01-01,
    date_to=Y-12-31) ma khong can go tay tung ngay. Neu vua co year vua co
    date_from/date_to, ca hai cung ap dung (AND) - year se tu thu hep, thuong
    dung 1 trong 2 cach la du.
    feedback: None/"" = tất cả; "up"/"down" = đã đánh giá 👍/👎; "none" = chưa
    đánh giá.
    """
    conditions = []
    params = []
    if status == "ok":
        conditions.append("blocked = 0")
    elif status == "blocked":
        conditions.append(
            "block_stage IN ('input_guardrail', 'llm_not_applicable', 'sql_validator', 'output_guardrail')"
        )
    elif status == "error":
        conditions.append("block_stage = 'service_error'")
    if date_from:
        conditions.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("created_at <= ?")
        params.append(date_to + "T23:59:59")
    if year:
        conditions.append("created_at LIKE ?")
        params.append(f"{year}-%")
    if feedback in ("up", "down"):
        conditions.append("feedback = ?")
        params.append(feedback)
    elif feedback == "none":
        conditions.append("(feedback IS NULL OR feedback = '')")
    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = _connect()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT * FROM request_logs {where_sql} ORDER BY id DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_available_years() -> list:
    """Danh sách năm THẬT co du lieu trong logs.db (khong phai list co dinh) -
    phuc vu dropdown "Nam" tren /admin, luon khop voi du lieu hien co."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT substr(created_at, 1, 4) AS y FROM request_logs "
            "WHERE created_at IS NOT NULL ORDER BY y DESC"
        ).fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        conn.close()


def fetch_stats() -> dict:
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) FROM request_logs").fetchone()[0]
        blocked = conn.execute(
            "SELECT COUNT(*) FROM request_logs WHERE blocked = 1"
        ).fetchone()[0]
        avg_ms = conn.execute(
            "SELECT AVG(ms_total) FROM request_logs WHERE blocked = 0"
        ).fetchone()[0]
        return {"total": total, "blocked": blocked, "avg_ms": round(avg_ms or 0)}
    finally:
        conn.close()


def fetch_stage_avg_ms(limit: int = None) -> dict:
    """Trung bình thời gian từng giai đoạn (LLM sinh SQL / DB thực thi / LLM diễn
    giải) tính trên các request THÀNH CÔNG (blocked = 0) - phục vụ thanh breakdown
    thời gian trên /admin.

    limit: chỉ tính trên N request thành công GẦN NHẤT (theo id giảm dần) - None
    nghĩa là tính trên toàn bộ. Cho phép người xem /admin tự chọn cỡ mẫu (10/50/
    100/tất cả) thay vì luôn cố định trên toàn bộ lịch sử, vì trung bình trên toàn
    bộ dễ bị các request rất cũ (trước khi tối ưu index/prompt) kéo lệch.
    """
    conn = _connect()
    try:
        if limit:
            row = conn.execute(
                """
                SELECT AVG(ms_generate_sql), AVG(ms_db_exec), AVG(ms_explain), COUNT(*)
                FROM (
                    SELECT ms_generate_sql, ms_db_exec, ms_explain
                    FROM request_logs
                    WHERE blocked = 0
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (limit,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT AVG(ms_generate_sql), AVG(ms_db_exec), AVG(ms_explain), COUNT(*)
                FROM request_logs
                WHERE blocked = 0
                """
            ).fetchone()
        return {
            "generate_sql": round(row[0] or 0),
            "db_exec": round(row[1] or 0),
            "explain": round(row[2] or 0),
            "count": row[3] or 0,
        }
    finally:
        conn.close()


def fetch_latency_percentiles() -> dict:
    """P50 / P90 / P99 của ms_total trên các request THÀNH CÔNG - percentile
    phản ánh trải nghiệm thực tế tốt hơn AVG (1 request bị treo lâu không kéo
    lệch percentile như nó kéo lệch trung bình cộng).

    Tính bằng Python (nearest-rank, sort toàn bộ giá trị) thay vì SQL, vì SQLite
    không có PERCENTILE_CONT sẵn và lượng dữ liệu ở quy mô demo nội bộ này (vài
    nghìn dòng) sort trong Python vẫn rất nhanh, không cần optimize thêm.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT ms_total FROM request_logs WHERE blocked = 0 AND ms_total IS NOT NULL ORDER BY ms_total"
        ).fetchall()
        values = [r[0] for r in rows]
        n = len(values)
        if not n:
            return {"p50": 0, "p90": 0, "p99": 0, "count": 0}

        def _pct(p: float) -> int:
            # nearest-rank: phan tu thu ceil(p/100 * n), 1-indexed, kep trong [1, n]
            import math
            idx = min(n, max(1, math.ceil(p / 100 * n)))
            return values[idx - 1]

        return {"p50": _pct(50), "p90": _pct(90), "p99": _pct(99), "count": n}
    finally:
        conn.close()


def fetch_token_stats() -> dict:
    """Tổng token đã dùng (input/output/cache-read) - cộng trên MỌI request có
    ghi nhận usage (kể cả request bị guardrail/validator chặn SAU khi đã gọi
    LLM ít nhất 1 lần, vì token đó vẫn bị tính tiền thật dù câu trả lời bị
    chặn không trả về user). Request bị chặn TRƯỚC khi gọi LLM (input_guardrail)
    có input_tokens NULL nên không được tính vào đây - đúng bản chất, vì
    provider chưa hề nhận request nào.
    """
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens), COUNT(*)
            FROM request_logs
            WHERE input_tokens IS NOT NULL
            """
        ).fetchone()
        return {
            "input_tokens": row[0] or 0,
            "output_tokens": row[1] or 0,
            "cache_read_tokens": row[2] or 0,
            "requests_with_usage": row[3] or 0,
        }
    finally:
        conn.close()


def fetch_status_breakdown() -> list:
    """Đếm số request theo trạng thái - phục vụ biểu đồ tròn trên /admin.

    'OK' gộp mọi request không bị chặn (block_stage NULL); các trạng thái còn
    lại lấy nguyên block_stage đã ghi trong agent.py (input_guardrail,
    llm_not_applicable, sql_validator, output_guardrail, service_error).
    """
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT COALESCE(block_stage, 'ok') AS status, COUNT(*) AS n
            FROM request_logs
            GROUP BY status
            """
        ).fetchall()
        return [{"status": r[0], "count": r[1]} for r in rows]
    finally:
        conn.close()
