"""
Centralized application configuration.

All values are overridable via environment variables (see .env.example).
Docker Compose injects DATABASE_URL / REDIS_URL automatically; for local
non-Docker dev, copy .env.example to .env and adjust as needed.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "Netflix-Style Recommendation Engine"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/netflix_rec"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    RECOMMENDATION_CACHE_TTL_SECONDS: int = 60 * 15  # 15 minutes

    # --- Auth / JWT ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # --- OAuth (Google login) ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 120

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # --- ML ---
    ML_DATA_DIR: str = "data"
    HYBRID_ALPHA_DEFAULT: float = 0.6  # weight given to collaborative vs content score


@lru_cache
def get_settings() -> Settings:
    return Settings()
