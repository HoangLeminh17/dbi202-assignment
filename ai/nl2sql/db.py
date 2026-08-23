"""Ket noi DB read-only cho NL2SQL Agent.

San xuat that PHAI tro vao 1 SQL Server login chi co quyen SELECT tren
vw_game_sales_full (GRANT SELECT ON vw_game_sales_full TO nl2sql_readonly;
KHONG cap quyen tren bang goc) - khong bao gio dung sa/admin. Ben duoi ho tro
ca Windows Authentication (chi cho moi truong local/dev) khi khong co
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
    """Chay 1 cau SELECT (da qua sql_validator) va tra ve (columns, rows)."""
    conn = pyodbc.connect(_connection_string(), timeout=CONFIG.query_timeout_seconds)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        rows = [tuple(row) for row in cursor.fetchall()]
        return columns, rows
    finally:
        conn.close()
