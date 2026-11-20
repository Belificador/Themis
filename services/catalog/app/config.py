from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "catalog-service"
    database_url: str = "postgresql+asyncpg://catalog:catalog@localhost:5433/catalog"
    media_dir: str = "./media"
    image_max_bytes: int = 5 * 1024 * 1024
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_bucket_product_images: str = "product-images"
    # Supabase PostgreSQL (esquema por servicio)
    supabase_ref: str = "yeaylufnjeyiutyxqict"
    supabase_db_password: str = ""
    db_schema: str = "catalog"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
