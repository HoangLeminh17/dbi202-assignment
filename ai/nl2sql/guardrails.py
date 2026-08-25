"""Guardrail input/output - lớp bảo vệ đơn giản, đủ dùng cho demo nội bộ.

Lọc domain (câu hỏi có thuộc chủ đề doanh số game hay không) được giao cho
chính LLM quyết định qua system prompt (xem llm_client.NOT_APPLICABLE) thay
vì so khớp từ khóa - từ khóa tĩnh dễ chặn nhầm câu hỏi diễn đạt khác thường
(vd không dùng đúng từ trong danh sách) trong khi LLM hiểu ngữ nghĩa tốt hơn
nhiều. check_input() ở đây chỉ giữ lại việc chặn prompt injection, vì đó vẫn
là ranh giới bảo mật cần chặn TRƯỚC khi gọi LLM (không thể giao cho LLM tự
xử lý an toàn).

Rate limit theo IP nằm ở webapp.py (route /ask), không phải ở module này -
đây là mối quan tâm tầng HTTP request, không phải tầng nội dung câu hỏi.

Sản xuất thật (nhiều instance/process) cần thêm: rate limit dùng store dùng
chung (vd Redis) thay vì in-memory per-process như hiện tại, và grounding
check chặt chẽ hơn (xem ai/NL2SQL_ARCHITECTURE.md mục 4).
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


# Bat mot "cum so" day du, cho phep nhieu nhom cach nhau boi dau . hoac , (vd
# "1.000.000" hoac "1,27") thay vi chi 1 dau phan cach nhu regex cu - regex cu
# tach "1.000.000" thanh 2 token roi ("1.000", "000") khong khop voi so goc
# "1000000" trong SQL/ket qua, gay bao hallucination oan (false positive).
_NUMBER_TOKEN_RE = re.compile(r"\d[\d.,]*\d|\d")
# Nhom hang nghin kieu Viet: cac nhom sau dau "." deu du 3 chu so (vd
# "1.000.000"), co the co phan thap phan sau dau "," o cuoi (vd "1.234.567,89").
_VN_THOUSANDS_RE = re.compile(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$")


def _canonicalize_number(token: str) -> str:
    """Quy 1 token so ve dang chuan de so sanh (dau '.' lam phan cach thap phan,
    khong co phan cach hang nghin) - khop voi dinh dang so trong SQL/du lieu.

    - "1.000.000" (hang nghin kieu Viet, nhieu nhom du 3 chu so sau dau ".") ->
      "1000000".
    - "1.234.567,89" -> "1234567.89".
    - Cac truong hop con lai (vd "82.74", "1,27") giu logic cu: chi co 1 dau
      phan cach, dau "," duoc coi la dau thap phan kieu Viet -> doi thanh ".".
    """
    if _VN_THOUSANDS_RE.match(token):
        int_part, _, frac_part = token.partition(",")
        int_part = int_part.replace(".", "")
        return f"{int_part}.{frac_part}" if frac_part else int_part
    return token.replace(",", ".")


def _extract_numbers(text: str) -> set:
    return {_canonicalize_number(tok) for tok in _NUMBER_TOKEN_RE.findall(text)}


def check_output(answer_text: str, sql: str, result_values: list) -> None:
    """Grounding check đơn giản: mọi con số LLM nêu ra phải xuất hiện trong kết quả SQL
    hoặc trong chính câu SQL (vd năm/điều kiện trong WHERE, LLM nhắc lại từ câu hỏi).

    Số được trích xuất theo substring (không ép full-string) để khớp cả trường hợp số
    nằm trong 1 giá trị text (vd game_name = "Yokai Watch 3"). Dấu phẩy thập phân kiểu
    Việt (vd "1,27") và dấu chấm phân cách hàng nghìn kiểu Việt (vd "1.000.000") đều
    được chuẩn hoá về 1 dạng chung trước khi so sánh (xem _canonicalize_number), vì LLM
    có thể viết số theo kiểu Việt trong khi dữ liệu SQL luôn dùng dấu chấm thập phân,
    không có phân cách hàng nghìn. Đây là kiểm tra xấp xỉ (so khớp chuỗi số, không parse
    ngữ nghĩa), đủ để bắt hallucination rõ ràng (LLM tự "bịa" thêm số liệu không có
    trong kết quả truy vấn).
    """
    numbers_in_answer = _extract_numbers(answer_text)
    if not numbers_in_answer:
        return

    allowed_numbers = _extract_numbers(sql)
    for v in result_values:
        allowed_numbers.update(_extract_numbers(str(v)))

    ungrounded = [n for n in numbers_in_answer if n not in allowed_numbers]
    if ungrounded:
        raise GuardrailError(
            f"Câu trả lời chứa số liệu không khớp kết quả SQL: {ungrounded}"
        )
