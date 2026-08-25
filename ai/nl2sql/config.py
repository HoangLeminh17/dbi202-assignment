"""Đọc cấu hình từ file .env (không commit .env thật, xem ai/.env.example)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    db_server: str = os.getenv("DB_SERVER", "localhost")
    db_name: str = os.getenv("DB_NAME", "Group7")
    db_readonly_user: str = os.getenv("DB_READONLY_USER", "")
    db_readonly_password: str = os.getenv("DB_READONLY_PASSWORD", "")

    max_rows: int = int(os.getenv("MAX_ROWS", "100"))
    query_timeout_seconds: int = int(os.getenv("QUERY_TIMEOUT_SECONDS", "30"))

    admin_user: str = os.getenv("ADMIN_USER", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")

    # Gia tien tu dien qua .env (USD / 1 trieu token) - KHONG hardcode gia that
    # trong code vi gia cua provider thay doi theo thoi gian va theo model, de
    # sai gia se hien thi chi phi sai lech that. Mac dinh 0 = "chua cau hinh",
    # /admin se hien "chưa cấu hình giá" thay vi mot con so $0.00 gay hieu lam.
    price_per_1m_input: float = float(os.getenv("PRICE_PER_1M_INPUT_TOKENS") or 0)
    price_per_1m_output: float = float(os.getenv("PRICE_PER_1M_OUTPUT_TOKENS") or 0)


CONFIG = Config()
