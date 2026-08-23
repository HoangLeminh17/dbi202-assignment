"""Guardrail input/output - lớp bảo vệ đơn giản, đủ dùng cho demo nội bộ.

Lọc domain (câu hỏi có thuộc chủ đề doanh số game hay không) được giao cho
chính LLM quyết định qua system prompt (xem llm_client.NOT_APPLICABLE) thay
vì so khớp từ khóa - từ khóa tĩnh dễ chặn nhầm câu hỏi diễn đạt khác thường
(vd không dùng đúng từ trong danh sách) trong khi LLM hiểu ngữ nghĩa tốt hơn
nhiều. check_input() ở đây chỉ giữ lại việc chặn prompt injection, vì đó vẫn
là ranh giới bảo mật cần chặn TRƯỚC khi gọi LLM (không thể giao cho LLM tự
xử lý an toàn).

Sản xuất thật cần thêm: rate limit theo user/IP, và grounding check chặt chẽ
hơn (xem ai/NL2SQL_ARCHITECTURE.md mục 4).
"""
import re
import unicodedata

INJECTION_PATTERNS = [
    # \b...\b{0,20 ky tu} cho phep nhieu tu dem (vd "ignore all previous
    # instructions") thay vi chi khop dung 1 tu dem nhu ban cu - phat hien qua
    # test_blocks_ignore_instructions_english (ai/nl2sql/tests/test_guardrails.py).
    r"ignore\b.{0,20}\binstructions\b",
    r"bỏ qua\b.{0,20}\b(hướng dẫn|chỉ dẫn|instructions)",
    r"drop\s+table",
    r"delete\s+from",
    r"update\s+\w+\s+set",
    r"insert\s+into",
    r"xp_cmdshell",
    r"exec(ute)?\s*\(",
    r"--\s*$",
    r";\s*--",
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
    """Chặn prompt injection. Lọc domain do LLM tự quyết định (xem module docstring)."""
    lowered = _strip_accents(question.lower())

    for pattern in INJECTION_PATTERNS:
        if re.search(_strip_accents(pattern), lowered):
            raise GuardrailError(f"Phát hiện pattern nghi injection: '{pattern}'")


def check_output(answer_text: str, sql: str, result_values: list) -> None:
    """Grounding check đơn giản: mọi con số LLM nêu ra phải xuất hiện trong kết quả SQL
    hoặc trong chính câu SQL (vd năm/điều kiện trong WHERE, LLM nhắc lại từ câu hỏi).

    Số được trích xuất theo substring (không ép full-string) để khớp cả trường hợp số
    nằm trong 1 giá trị text (vd game_name = "Yokai Watch 3"). Dấu phẩy thập phân kiểu
    Việt (vd "1,27") được chuẩn hoá về dấu chấm trước khi so sánh, vì LLM có thể viết
    số theo kiểu Việt trong khi dữ liệu SQL luôn dùng dấu chấm. Đây là kiểm tra xấp xỉ
    (so khớp chuỗi số, không parse ngữ nghĩa), đủ để bắt hallucination rõ ràng (LLM tự
    "bịa" thêm số liệu không có trong kết quả truy vấn).
    """

    def _normalize(numbers):
        return {n.replace(",", ".") for n in numbers}

    numbers_in_answer = _normalize(re.findall(r"\d+(?:[.,]\d+)?", answer_text))
    if not numbers_in_answer:
        return

    allowed_numbers = _normalize(re.findall(r"\d+(?:[.,]\d+)?", sql))
    for v in result_values:
        allowed_numbers.update(_normalize(re.findall(r"\d+(?:[.,]\d+)?", str(v))))

    ungrounded = [n for n in numbers_in_answer if n not in allowed_numbers]
    if ungrounded:
        raise GuardrailError(
            f"Câu trả lời chứa số liệu không khớp kết quả SQL: {ungrounded}"
        )
