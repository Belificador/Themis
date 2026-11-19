from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "sales-service"
    database_url: str = (
        "postgresql+asyncpg://sales:sales@localhost:5436/sales"
    )
    catalog_url: str = "http://localhost:8001"
    inventory_url: str = "http://localhost:8002"
    request_timeout_seconds: float = 20.0
    media_dir: str = "./media"
    invoice_max_bytes: int = 10 * 1024 * 1024
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket_invoices: str = "sales-invoices"
    supabase_ref: str = "yeaylufnjeyiutyxqict"
    supabase_db_password: str = ""
    db_schema: str = "sales"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
