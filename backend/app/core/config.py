from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5-mini"
    DATABASE_URL: str = "sqlite:///./word_chain.db"
    TRACE_LOG_PATH: str = "./traces.jsonl"
    MAX_LLM_RETRIES: int = 3
    MAX_NO_S_RETRIES: int = 5

    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"))

    @field_validator("TRACE_LOG_PATH")
    @classmethod
    def _anchor_trace_log_path(cls, v: str) -> str:
        path = Path(v)
        return v if path.is_absolute() else str(BACKEND_DIR / path)

    @field_validator("DATABASE_URL")
    @classmethod
    def _anchor_database_url(cls, v: str) -> str:
        prefix = "sqlite:///"
        if not v.startswith(prefix):
            return v
        raw_path = Path(v[len(prefix) :])
        if raw_path.is_absolute():
            return v
        return prefix + str(BACKEND_DIR / raw_path)


settings = Settings()
