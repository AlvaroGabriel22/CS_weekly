from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Quality Weekly Intelligence"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://qwi:qwi_secret@localhost:5432/qwi_db"

    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # ── Provedor de LLM ────────────────────────────────────────────────────
    # "ollama" (local, padrão) ou "openai_compat" (API externa compatível com
    # OpenAI — chat/completions). Para trocar, basta o .env:
    #   LLM_PROVIDER=openai_compat
    #   LLM_BASE_URL=https://sua-api/v1
    #   LLM_API_KEY=...            (se a API exigir)
    #   LLM_MODEL=gpt-4o
    # Tudo (tradução, copiloto do gestor, deck em um clique…) passa a usar a
    # API automaticamente, com fila de LLM_RATE_LIMIT_PER_MIN requisições/min
    # e fallback para o Ollama local quando a API estiver indisponível.
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    LLM_RATE_LIMIT_PER_MIN: int = 3
    LLM_FALLBACK_TO_OLLAMA: bool = True

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:e2b"
    # Context window for Ollama. The default (4096) truncates the weekly
    # evidence dossier, producing empty responses (done_reason=length).
    OLLAMA_NUM_CTX: int = 16384
    OLLAMA_NUM_PREDICT: int = 4096

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
