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
"""
import threading

import pyodbc

from .config import CONFIG

_conn = None
_lock = threading.Lock()


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
    """Chạy 1 câu SELECT (đã qua sql_validator) và trả về (columns, rows)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [c[0] for c in cursor.description]
    rows = [tuple(row) for row in cursor.fetchall()]
    return columns, rows
