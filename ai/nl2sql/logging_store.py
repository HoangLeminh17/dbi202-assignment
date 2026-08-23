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
    return conn


def record(**fields) -> None:
    conn = _connect()
    try:
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        conn.execute(
            f"INSERT INTO request_logs ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        conn.commit()
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
