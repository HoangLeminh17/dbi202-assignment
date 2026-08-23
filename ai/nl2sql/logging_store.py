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
    # feedback duoc them sau ban dau (CREATE TABLE IF NOT EXISTS khong tu
    # them cot moi vao bang cu da ton tai) - migrate bang ALTER, bo qua neu
    # cot da co san.
    try:
        conn.execute("ALTER TABLE request_logs ADD COLUMN feedback TEXT")
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


def fetch_recent(limit: int = 200) -> list:
    conn = _connect()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM request_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
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
