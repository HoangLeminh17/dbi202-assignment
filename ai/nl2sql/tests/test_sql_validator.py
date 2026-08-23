"""Test cho SQL validator (ai/nl2sql/sql_validator.py) - lop quan trong nhat:
chan DML/DDL, ep whitelist bang/view, tu dong gioi han so dong.
"""
import pytest

from ai.nl2sql.sql_validator import SQLValidationError, validate_and_enforce_limit


def test_allows_valid_select_on_whitelisted_view():
    sql = validate_and_enforce_limit(
        "SELECT TOP 5 game_name, SUM(num_sales) FROM vw_game_sales_full GROUP BY game_name"
    )
    assert "vw_game_sales_full" in sql.lower()


def test_adds_limit_when_missing():
    sql = validate_and_enforce_limit("SELECT game_name FROM vw_game_sales_full")
    assert "top" in sql.lower() or "limit" in sql.lower()


def test_keeps_existing_top_unchanged():
    sql = validate_and_enforce_limit(
        "SELECT TOP 3 game_name FROM vw_game_sales_full", max_rows=100
    )
    assert "top 3" in sql.lower()


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE vw_game_sales_full",
        "DELETE FROM vw_game_sales_full",
        "UPDATE vw_game_sales_full SET num_sales = 0",
        "INSERT INTO vw_game_sales_full VALUES (1)",
        "ALTER TABLE vw_game_sales_full ADD col INT",
        "EXEC xp_cmdshell 'dir'",
    ],
)
def test_blocks_dml_ddl(sql):
    with pytest.raises(SQLValidationError):
        validate_and_enforce_limit(sql)


def test_blocks_table_outside_whitelist():
    with pytest.raises(SQLValidationError):
        validate_and_enforce_limit("SELECT * FROM region_sales")


def test_blocks_multiple_statements():
    with pytest.raises(SQLValidationError):
        validate_and_enforce_limit(
            "SELECT * FROM vw_game_sales_full; DROP TABLE vw_game_sales_full;"
        )


def test_blocks_non_select_statement():
    with pytest.raises(SQLValidationError):
        validate_and_enforce_limit("CREATE VIEW x AS SELECT 1")


def test_blocks_unparseable_sql():
    with pytest.raises(SQLValidationError):
        validate_and_enforce_limit("SELEKT * FORM vw_game_sales_full !!!")
