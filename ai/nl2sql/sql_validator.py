"""SQL Validator - lớp quan trọng nhất của pipeline (xem NL2SQL_ARCHITECTURE.md mục 4).

Dùng sqlglot parse SQL thành AST (không dùng regex) để:
  1. Chỉ chấp nhận 1 câu SELECT duy nhất.
  2. Chặn cứng mọi node DML/DDL (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE...).
  3. Whitelist bảng/view được phép truy vấn (mặc định: vw_game_sales_full).
  4. Bắt buộc có giới hạn số dòng trả về (TOP/LIMIT) - tự động thêm nếu thiếu.
"""
import sqlglot
from sqlglot import exp

from .schema import ALLOWED_TABLES

FORBIDDEN_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Merge,
    exp.TruncateTable,
)


class SQLValidationError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def validate_and_enforce_limit(
    sql: str, allowed_tables: set = ALLOWED_TABLES, max_rows: int = 100
) -> str:
    try:
        statements = sqlglot.parse(sql, read="tsql")
    except Exception as exc:
        raise SQLValidationError(f"SQL không parse được: {exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SQLValidationError("Chỉ cho phép dùng 1 câu lệnh SQL duy nhất.")

    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        raise SQLValidationError(
            f"Chỉ cho phép SELECT, phát hiện: {type(stmt).__name__}"
        )

    for node in stmt.walk():
        if isinstance(node, FORBIDDEN_NODE_TYPES):
            raise SQLValidationError(
                f"Phát hiện lệnh không được phép trong SQL: {type(node).__name__}"
            )

    tables = {t.name.lower() for t in stmt.find_all(exp.Table)}
    allowed_lower = {t.lower() for t in allowed_tables}
    not_allowed = tables - allowed_lower
    if not_allowed:
        raise SQLValidationError(
            f"Bảng/view không nằm trong whitelist cho phép: {sorted(not_allowed)}"
        )

    if stmt.args.get("limit") is None:
        stmt.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return stmt.sql(dialect="tsql")
