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

Output guardrail (fill_and_verify_template) dùng cơ chế placeholder
{tên_cột:số_dòng} thay vì validate hậu kiểm câu văn tự do bằng regex - xem
docstring của hàm đó để biết vì sao (bắt được cả trường hợp số thật nhưng
gán sai thực thể, không chỉ số bịa hoàn toàn).

Sản xuất thật (nhiều instance/process) cần thêm: rate limit dùng store dùng
chung (vd Redis) thay vì in-memory per-process như hiện tại.
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


# {ten_cot:so_dong} - vd {game_name:0}, {total_sales:0}. So dong 0-indexed,
# khop voi cach danh so trong prompt cua explain_result() (llm_client.py).
_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*):(\d+)\}")


def fill_and_verify_template(template: str, sql: str, columns: list, rows: list) -> str:
    """Điền placeholder {tên_cột:số_dòng} bằng giá trị THẬT đọc thẳng từ `rows`
    (không phải từ text LLM viết) rồi trả về câu trả lời hoàn chỉnh.

    Đây là lớp thay thế check_output() cũ (vốn chỉ so khớp số bằng regex sau
    khi LLM đã viết xong câu tự do) - cách cũ bắt được số BỊA nhưng KHÔNG bắt
    được số THẬT bị gán nhầm cho thực thể sai (vd nói "FIFA 17 dẫn đầu với
    82.74 triệu bản" trong khi 82.74 thực ra là của Wii Sports) vì con số đó
    vẫn "có thật" trong kết quả, chỉ sai chỗ gán. Với placeholder, giá trị lẫn
    tên thực thể đều lấy thẳng từ đúng ô dữ liệu LLM tham chiếu - LLM chỉ được
    chọn ô nào, không được tự quyết định giá trị của ô đó là gì.

    Chặn (raise GuardrailError) khi:
    - Placeholder tham chiếu cột không tồn tại trong `columns`.
    - Placeholder tham chiếu số dòng vượt quá `len(rows)`.
    - Phần văn bản NGOÀI placeholder còn sót chữ số - nghĩa là LLM lách bằng
      cách gõ thẳng số vào câu thay vì dùng placeholder. Ngoại lệ: số đó xuất
      hiện y hệt trong chính câu SQL (vd LLM nhắc lại năm trong điều kiện
      WHERE khi kết quả rỗng) - không phải bịa, chỉ là nhắc lại điều kiện lọc.
    """
    col_index = {c: i for i, c in enumerate(columns)}

    def _replace(m: re.Match) -> str:
        col, row_idx_s = m.group(1), m.group(2)
        row_idx = int(row_idx_s)
        if col not in col_index:
            raise GuardrailError(f"Câu trả lời tham chiếu cột không tồn tại: '{col}'")
        if row_idx >= len(rows):
            raise GuardrailError(f"Câu trả lời tham chiếu dòng không tồn tại: dòng {row_idx}")
        value = rows[row_idx][col_index[col]]
        return "không có dữ liệu" if value is None else str(value)

    filled = _PLACEHOLDER_RE.sub(_replace, template)

    residual_text = _PLACEHOLDER_RE.sub("", template)
    leaked_numbers = _extract_numbers(residual_text) - _extract_numbers(sql)
    if leaked_numbers:
        raise GuardrailError(
            f"Câu trả lời chứa số không thông qua placeholder dữ liệu thật: {leaked_numbers}"
        )

    return filled
