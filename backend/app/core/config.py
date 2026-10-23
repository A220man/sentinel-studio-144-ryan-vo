from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Sentinel Studio"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sentinel.db"

    # Security
    SECRET_KEY: str = "change-me-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Keycloak OIDC
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "sentinel"
    KEYCLOAK_CLIENT_ID: str = "sentinel-studio"
    KEYCLOAK_CLIENT_SECRET: str = ""
    KEYCLOAK_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    @property
    def KEYCLOAK_ISSUER_URL(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}"

    @property
    def KEYCLOAK_AUTH_URL(self) -> str:
        return f"{self.KEYCLOAK_ISSUER_URL}/protocol/openid-connect/auth"

    @property
    def KEYCLOAK_TOKEN_URL(self) -> str:
        return f"{self.KEYCLOAK_ISSUER_URL}/protocol/openid-connect/token"

    @property
    def KEYCLOAK_JWKS_URL(self) -> str:
        return f"{self.KEYCLOAK_ISSUER_URL}/protocol/openid-connect/certs"

    @property
    def KEYCLOAK_LOGOUT_URL(self) -> str:
        return f"{self.KEYCLOAK_ISSUER_URL}/protocol/openid-connect/logout"

    @property
    def KEYCLOAK_USERINFO_URL(self) -> str:
        return f"{self.KEYCLOAK_ISSUER_URL}/protocol/openid-connect/userinfo"

    # LLM Provider
    LLM_PROVIDER: str = "openai-compatible"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""

    # Demo mode
    DEMO_MODE: bool = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()