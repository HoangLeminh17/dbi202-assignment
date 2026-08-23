"""Guardrail input/output - lop bao ve don gian, du dung cho demo noi bo.

San xuat that can them: intent classifier bang model rieng, rate limit theo
user/IP, va grounding check chat che hon (xem ai/NL2SQL_ARCHITECTURE.md muc 4b).
"""
import re

INJECTION_PATTERNS = [
    r"ignore (all|previous|above) instructions",
    r"bo qua (huong dan|chi dan|instructions)",
    r"drop\s+table",
    r"delete\s+from",
    r"update\s+\w+\s+set",
    r"insert\s+into",
    r"xp_cmdshell",
    r"exec(ute)?\s*\(",
    r"--\s*$",
    r";\s*--",
]

DOMAIN_KEYWORDS = [
    "game", "doanh so", "sales", "publisher", "phat hanh", "the loai", "genre",
    "nen tang", "platform", "khu vuc", "region", "nam", "year", "top",
]


class GuardrailError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def check_input(question: str) -> None:
    """Chan prompt injection va cau hoi ngoai domain (business: video game sales)."""
    lowered = question.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            raise GuardrailError(f"Phat hien pattern nghi injection: '{pattern}'")

    if not any(kw in lowered for kw in DOMAIN_KEYWORDS):
        raise GuardrailError(
            "Cau hoi khong thuoc pham vi du lieu doanh so game (genre/platform/"
            "publisher/region/nam)."
        )


def check_output(answer_text: str, result_values: list) -> None:
    """Grounding check don gian: moi con so LLM neu ra phai xuat hien trong ket qua SQL.

    Day la kiem tra xap xi (so khop chuoi so, khong parse ngu nghia), du de bat
    hallucination ro rang (LLM tu 'bia' them so lieu khong co trong ket qua truy van).
    """
    numbers_in_answer = set(re.findall(r"\d+(?:[.,]\d+)?", answer_text))
    if not numbers_in_answer:
        return

    numbers_in_result = {str(v) for v in result_values}
    ungrounded = [n for n in numbers_in_answer if n not in numbers_in_result]
    if ungrounded:
        raise GuardrailError(
            f"Cau tra loi chua so lieu khong khop ket qua SQL: {ungrounded}"
        )
