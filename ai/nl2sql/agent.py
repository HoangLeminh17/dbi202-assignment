"""NL2SQL Agent - điều phối pipeline đầy đủ (xem NL2SQL_ARCHITECTURE.md mục 1):

  guardrail input -> NL2SQL (LLM) -> SQL validator -> DB read-only
  -> LLM diễn giải -> guardrail output -> kết quả + log.

Dùng nội bộ (nhóm/lớp), không deploy public. Chạy thử:
  python -m ai.nl2sql.agent --question "Top 5 game bán chạy nhất ở Nhật năm 2016"
"""
import argparse
import logging
from dataclasses import dataclass, field

from . import db, llm_client
from .config import CONFIG
from .guardrails import GuardrailError, check_input, check_output
from .sql_validator import SQLValidationError, validate_and_enforce_limit

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("nl2sql")


@dataclass
class AgentResult:
    question: str
    blocked: bool = False
    reason: str = ""
    sql: str = ""
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    answer: str = ""


def ask(question: str) -> AgentResult:
    result = AgentResult(question=question)

    try:
        check_input(question)
    except GuardrailError as exc:
        logger.warning("Input guardrail block: %s", exc.reason)
        result.blocked, result.reason = True, exc.reason
        return result

    raw_sql = llm_client.generate_sql(question)
    logger.info("LLM sinh SQL: %s", raw_sql)

    if raw_sql.strip().upper() == llm_client.NOT_APPLICABLE:
        logger.warning("LLM đánh giá câu hỏi ngoài phạm vi dữ liệu")
        result.blocked = True
        result.reason = "Câu hỏi không thể trả lời bằng dữ liệu doanh số game (do LLM đánh giá)."
        return result

    try:
        safe_sql = validate_and_enforce_limit(raw_sql, max_rows=CONFIG.max_rows)
    except SQLValidationError as exc:
        logger.warning("SQL validator block: %s", exc.reason)
        result.blocked, result.reason = True, exc.reason
        return result
    result.sql = safe_sql
    logger.info("SQL đã validate: %s", safe_sql)

    columns, rows = db.execute_select(safe_sql)
    result.columns, result.rows = columns, rows
    logger.info("Kết quả: %d dòng", len(rows))

    answer = llm_client.explain_result(question, safe_sql, rows)

    flat_values = [v for row in rows for v in row]
    try:
        check_output(answer, safe_sql, flat_values)
    except GuardrailError as exc:
        logger.warning("Output guardrail block: %s", exc.reason)
        result.blocked, result.reason = True, exc.reason
        return result

    result.answer = answer
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NL2SQL Agent (nội bộ)")
    parser.add_argument("--question", required=True)
    args = parser.parse_args()

    out = ask(args.question)
    if out.blocked:
        print(f"[BLOCKED] {out.reason}")
    else:
        print(f"SQL: {out.sql}")
        print(f"Answer: {out.answer}")
