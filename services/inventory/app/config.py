from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "inventory-service"
    database_url: str = (
        "postgresql+asyncpg://inventory:inventory@localhost:5434/inventory"
    )
    # Supabase PostgreSQL (esquema por servicio)
    supabase_ref: str = "yeaylufnjeyiutyxqict"
    supabase_db_password: str = ""
    db_schema: str = "inventory"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
