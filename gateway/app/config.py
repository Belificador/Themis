from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "api-gateway"
    catalog_url: str = "http://localhost:8001"
    inventory_url: str = "http://localhost:8002"
    notification_url: str = "http://localhost:8003"
    sales_url: str = "http://localhost:8004"
    static_dir: str = "/app/static"
    request_timeout_seconds: float = 30.0
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
