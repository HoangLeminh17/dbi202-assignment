"""Guardrail input/output - lớp bảo vệ đơn giản, đủ dùng cho demo nội bộ.

Sản xuất thật cần thêm: intent classifier bằng model riêng, rate limit theo
user/IP, và grounding check chặt chẽ hơn (xem ai/NL2SQL_ARCHITECTURE.md mục 4).
"""
import re
import unicodedata

INJECTION_PATTERNS = [
    r"ignore (all|previous|above) instructions",
    r"bỏ qua (hướng dẫn|chỉ dẫn|instructions)",
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
    # Tiếng Việt (có/không dấu đều so khớp được nhờ _strip_accents)
    "trò chơi", "game", "doanh số", "doanh thu", "bán chạy", "bán", "xếp hạng",
    "thống kê", "xu hướng", "nhà phát hành", "phát hành", "thể loại",
    "nền tảng", "khu vực", "vùng", "năm", "top",
    # English
    "video game", "sales", "revenue", "best-selling", "best selling",
    "publisher", "genre", "platform", "region", "year", "trend", "ranking",
]


def _strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp được cả câu hỏi gõ có dấu lẫn không dấu."""
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


class GuardrailError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def check_input(question: str) -> None:
    """Chặn prompt injection và câu hỏi ngoài domain (business: video game sales)."""
    lowered = _strip_accents(question.lower())

    for pattern in INJECTION_PATTERNS:
        if re.search(_strip_accents(pattern), lowered):
            raise GuardrailError(f"Phát hiện pattern nghi injection: '{pattern}'")

    if not any(_strip_accents(kw) in lowered for kw in DOMAIN_KEYWORDS):
        raise GuardrailError(
            "Câu hỏi không thuộc phạm vi dữ liệu doanh số game (genre/platform/"
            "publisher/region/năm)."
        )


def check_output(answer_text: str, sql: str, result_values: list) -> None:
    """Grounding check đơn giản: mọi con số LLM nêu ra phải xuất hiện trong kết quả SQL
    hoặc trong chính câu SQL (vd năm/điều kiện trong WHERE, LLM nhắc lại từ câu hỏi).

    Số được trích xuất theo substring (không ép full-string) để khớp cả trường hợp số
    nằm trong 1 giá trị text (vd game_name = "Yokai Watch 3"). Đây là kiểm tra xấp xỉ
    (so khớp chuỗi số, không parse ngữ nghĩa), đủ để bắt hallucination rõ ràng (LLM tự
    "bịa" thêm số liệu không có trong kết quả truy vấn).
    """
    numbers_in_answer = set(re.findall(r"\d+(?:[.,]\d+)?", answer_text))
    if not numbers_in_answer:
        return

    allowed_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", sql))
    for v in result_values:
        allowed_numbers.update(re.findall(r"\d+(?:[.,]\d+)?", str(v)))

    ungrounded = [n for n in numbers_in_answer if n not in allowed_numbers]
    if ungrounded:
        raise GuardrailError(
            f"Câu trả lời chứa số liệu không khớp kết quả SQL: {ungrounded}"
        )
