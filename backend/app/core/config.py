from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "operational-change-intelligence"
    environment: str = "local"
    database_url: str = Field(
        default="postgresql+psycopg://oci:oci_password@localhost:5432/oci",
        validation_alias="DATABASE_URL",
    )
    check_db_on_startup: bool = Field(
        default=True,
        validation_alias="APP_CHECK_DB_ON_STARTUP",
    )
    db_connect_timeout_seconds: int = Field(
        default=3,
        validation_alias="DB_CONNECT_TIMEOUT_SECONDS",
    )
    demo_mode: bool = Field(
        default=False,
        validation_alias="DEMO_MODE",
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
