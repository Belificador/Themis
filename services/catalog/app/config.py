from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "catalog-service"
    database_url: str = "postgresql+asyncpg://catalog:catalog@localhost:5433/catalog"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    products_exchange: str = "products"
    outbox_interval_seconds: float = 1.0
    media_dir: str = "./media"
    image_max_bytes: int = 5 * 1024 * 1024
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_bucket_product_images: str = "product-images"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
