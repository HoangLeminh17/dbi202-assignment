"""NL2SQL Agent - điều phối pipeline đầy đủ (xem NL2SQL_ARCHITECTURE.md mục 1):

  guardrail input -> NL2SQL (LLM) -> SQL validator -> DB read-only
  -> LLM diễn giải -> guardrail output -> kết quả + log.

Mỗi lần chạy (dù thành công hay bị chặn/lỗi) đều ghi 1 dòng vào
ai/nl2sql/logs.db (xem logging_store.py) - admin xem lại toàn bộ luồng qua
trang /admin của webapp.py (xem NL2SQL_ARCHITECTURE.md mục 7 - Monitoring).

Lỗi hạ tầng (LLM timeout, mất kết nối DB...) được bắt gọn, không để crash/treo
tiến trình - trả về AgentResult.error=True để phía web hiện thông báo bảo trì
thay vì đứng im vô thời hạn.

Dùng nội bộ (nhóm/lớp), không deploy public. Chạy thử:
  python -m ai.nl2sql.agent --question "Top 5 game bán chạy nhất ở Nhật năm 2016"
"""
import argparse
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import db, llm_client, logging_store
from .config import CONFIG
from .guardrails import GuardrailError, check_input, check_output
from .sql_validator import SQLValidationError, validate_and_enforce_limit

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("nl2sql")

MAINTENANCE_MESSAGE = (
    "Dịch vụ hiện đang bảo trì (không kết nối được LLM hoặc database), "
    "vui lòng thử lại sau."
)


@dataclass
class AgentResult:
    question: str
    blocked: bool = False
    error: bool = False
    reason: str = ""
    sql: str = ""
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    answer: str = ""


def _now_ms() -> float:
    return time.perf_counter() * 1000


def ask(question: str) -> AgentResult:
    result = AgentResult(question=question)
    t_start = _now_ms()
    ms_generate_sql = ms_db_exec = ms_explain = None
    raw_sql = ""

    def _save(blocked: bool, block_stage: str = None, reason: str = "") -> None:
        try:
            logging_store.record(
                created_at=datetime.now(timezone.utc).isoformat(),
                question=question,
                blocked=int(blocked),
                block_stage=block_stage,
                reason=reason,
                raw_sql=raw_sql,
                safe_sql=result.sql,
                row_count=len(result.rows),
                answer=result.answer,
                llm_provider=CONFIG.llm_provider,
                llm_model=getattr(CONFIG, f"{CONFIG.llm_provider}_model", ""),
                ms_generate_sql=ms_generate_sql,
                ms_db_exec=ms_db_exec,
                ms_explain=ms_explain,
                ms_total=int(_now_ms() - t_start),
            )
        except Exception:
            logger.exception("Ghi log vào logs.db thất bại (bỏ qua, không chặn response)")

    try:
        check_input(question)
    except GuardrailError as exc:
        logger.warning("Input guardrail block: %s", exc.reason)
        result.blocked, result.reason = True, exc.reason
        _save(True, "input_guardrail", exc.reason)
        return result

    try:
        t0 = _now_ms()
        raw_sql = llm_client.generate_sql(question)
        ms_generate_sql = int(_now_ms() - t0)
        logger.info("LLM sinh SQL: %s", raw_sql)

        if raw_sql.strip().upper() == llm_client.NOT_APPLICABLE:
            logger.warning("LLM đánh giá câu hỏi ngoài phạm vi dữ liệu")
            result.blocked = True
            result.reason = "Câu hỏi không thể trả lời bằng dữ liệu doanh số game (do LLM đánh giá)."
            _save(True, "llm_not_applicable", result.reason)
            return result

        try:
            safe_sql = validate_and_enforce_limit(raw_sql, max_rows=CONFIG.max_rows)
        except SQLValidationError as exc:
            logger.warning("SQL validator block: %s", exc.reason)
            result.blocked, result.reason = True, exc.reason
            _save(True, "sql_validator", exc.reason)
            return result
        result.sql = safe_sql
        logger.info("SQL đã validate: %s", safe_sql)

        t0 = _now_ms()
        columns, rows = db.execute_select(safe_sql)
        ms_db_exec = int(_now_ms() - t0)
        result.columns, result.rows = columns, rows
        logger.info("Kết quả: %d dòng", len(rows))

        t0 = _now_ms()
        answer = llm_client.explain_result(question, safe_sql, rows)
        ms_explain = int(_now_ms() - t0)
    except Exception as exc:  # timeout, mất mạng, DB lỗi, provider API lỗi...
        logger.exception("Lỗi hạ tầng khi xử lý câu hỏi")
        result.error = True
        result.reason = f"{MAINTENANCE_MESSAGE} (chi tiết: {exc})"
        _save(True, "service_error", str(exc))
        return result

    flat_values = [v for row in rows for v in row]
    try:
        check_output(answer, safe_sql, flat_values)
    except GuardrailError as exc:
        logger.warning("Output guardrail block: %s", exc.reason)
        result.blocked, result.reason = True, exc.reason
        _save(True, "output_guardrail", exc.reason)
        return result

    result.answer = answer
    _save(False)
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
