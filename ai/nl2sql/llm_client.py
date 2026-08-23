"""LLM client - truu tuong hoa provider ben ngoai (Claude / ChatGPT / Gemini).

Chon provider qua bien moi truong LLM_PROVIDER trong .env (xem ai/.env.example).
Chi import SDK cua provider dang dung (lazy import) de khong bat buoc cai ca 3.
"""
from .config import CONFIG
from .schema import build_prompt_context

SYSTEM_PROMPT = (
    "Ban la NL2SQL Agent noi bo cho database Group7 (video game sales) tren "
    "SQL Server. Chi sinh 1 cau SELECT T-SQL duy nhat tren view "
    "vw_game_sales_full, khong giai thich them, khong dung DML/DDL."
)


def _generate_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=CONFIG.anthropic_api_key)
    resp = client.messages.create(
        model=CONFIG.anthropic_model,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def _generate_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=CONFIG.openai_api_key)
    resp = client.chat.completions.create(
        model=CONFIG.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


def _generate_gemini(prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=CONFIG.google_api_key)
    model = genai.GenerativeModel(
        CONFIG.gemini_model, system_instruction=SYSTEM_PROMPT
    )
    return model.generate_content(prompt).text


_PROVIDERS = {
    "anthropic": _generate_anthropic,
    "openai": _generate_openai,
    "gemini": _generate_gemini,
}


def _call_llm(prompt: str) -> str:
    provider = CONFIG.llm_provider.lower()
    if provider not in _PROVIDERS:
        raise ValueError(f"LLM_PROVIDER khong ho tro: {provider}")
    return _PROVIDERS[provider](prompt)


def generate_sql(question: str) -> str:
    prompt = (
        f"{build_prompt_context()}\n\n"
        f"Cau hoi: {question}\n"
        "Chi tra loi bang 1 cau SQL, khong markdown, khong giai thich."
    )
    raw = _call_llm(prompt)
    return raw.strip().strip("`").removeprefix("sql").strip()


def explain_result(question: str, sql: str, rows: list) -> str:
    prompt = (
        f"Cau hoi cua nguoi dung: {question}\n"
        f"SQL da chay: {sql}\n"
        f"Ket qua ({len(rows)} dong dau): {rows[:20]}\n\n"
        "Dien giai ket qua tren thanh 1-2 cau tra loi tu nhien bang tieng Viet, "
        "CHI dung so lieu co trong ket qua, khong tu bia them so."
    )
    return _call_llm(prompt).strip()
