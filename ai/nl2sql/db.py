"""Kết nối DB read-only cho NL2SQL Agent.

Sản xuất thật PHẢI trỏ vào 1 SQL Server login chỉ có quyền SELECT trên
vw_game_sales_full (GRANT SELECT ON vw_game_sales_full TO nl2sql_readonly;
KHÔNG cấp quyền trên bảng gốc) - không bao giờ dùng sa/admin. Bên dưới hỗ trợ
cả Windows Authentication (chỉ cho môi trường local/dev) khi không có
DB_READONLY_USER trong .env.
"""
import pyodbc

from .config import CONFIG


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


def execute_select(sql: str):
    """Chạy 1 câu SELECT (đã qua sql_validator) và trả về (columns, rows)."""
    conn = pyodbc.connect(_connection_string(), timeout=CONFIG.query_timeout_seconds)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        rows = [tuple(row) for row in cursor.fetchall()]
        return columns, rows
    finally:
        conn.close()
