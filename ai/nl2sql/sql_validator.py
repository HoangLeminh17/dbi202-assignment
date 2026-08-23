"""SQL Validator - lop quan trong nhat cua pipeline (xem NL2SQL_ARCHITECTURE.md muc 4).

Dung sqlglot parse SQL thanh AST (khong dung regex) de:
  1. Chi chap nhan 1 cau SELECT duy nhat.
  2. Chan cung moi node DML/DDL (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE...).
  3. Whitelist bang/view duoc phep truy van (mac dinh: vw_game_sales_full).
  4. Bat buoc co gioi han so dong tra ve (TOP/LIMIT) - tu dong them neu thieu.
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
        raise SQLValidationError(f"SQL khong parse duoc: {exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SQLValidationError("Chi cho phep dung 1 cau lenh SQL duy nhat.")

    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        raise SQLValidationError(
            f"Chi cho phep SELECT, phat hien: {type(stmt).__name__}"
        )

    for node in stmt.walk():
        if isinstance(node, FORBIDDEN_NODE_TYPES):
            raise SQLValidationError(
                f"Phat hien lenh khong duoc phep trong SQL: {type(node).__name__}"
            )

    tables = {t.name.lower() for t in stmt.find_all(exp.Table)}
    allowed_lower = {t.lower() for t in allowed_tables}
    not_allowed = tables - allowed_lower
    if not_allowed:
        raise SQLValidationError(
            f"Bang/view khong nam trong whitelist cho phep: {sorted(not_allowed)}"
        )

    if stmt.args.get("limit") is None:
        stmt.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return stmt.sql(dialect="tsql")
