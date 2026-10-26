"""Vulture Bot - Application Configuration."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AIProvider(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    NONE = "none"


class EmailProvider(str, Enum):
    MOCK = "mock"
    GMAIL = "gmail"
    SMTP = "smtp"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Vulture Bot"
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = True
    app_secret_key: str = Field(
        default="CHANGE-ME-insecure-dev-key-do-not-use-in-production",
        min_length=32,
    )
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "sqlite+aiosqlite:///./vulture_bot.db"

    # AI Providers
    ai_provider: AIProvider = AIProvider.OLLAMA
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"

    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # Email
    email_provider: EmailProvider = EmailProvider.MOCK
    gmail_client_id: Optional[str] = None
    gmail_client_secret: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True

    # File Upload
    max_upload_size_mb: int = 50
    upload_dir: str = "./uploads"
    allowed_file_types: str = "csv,xlsx,xls,pdf,docx,doc,txt,json,xml"

    # Security
    session_cookie_name: str = "vulture_session"
    session_max_age: int = 86400  # 24 hours
    rate_limit_per_minute: int = 60
    admin_emails: str = ""

    # Redis
    redis_url: Optional[str] = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_file_types_list(self) -> list[str]:
        return [ft.strip().lower() for ft in self.allowed_file_types.split(",")]

    @property
    def admin_emails_list(self) -> list[str]:
        if not self.admin_emails:
            return []
        return [email.strip().lower() for email in self.admin_emails.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    def get_database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        url = self.database_url
        if "asyncpg" in url:
            return url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        if "aiosqlite" in url:
            return url.replace("sqlite+aiosqlite", "sqlite")
        return url


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings (useful for testing)."""
    global _settings
    _settings = None
