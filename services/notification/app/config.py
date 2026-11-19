from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "notification-service"
    database_url: str = (
        "postgresql+asyncpg://notification:notification@localhost:5435/notification"
    )
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    stock_exchange: str = "stock"
    notification_queue: str = "notification.stock_events"
    dedupe_window_seconds: int = 300
    max_attempts: int = 3
    # Supabase PostgreSQL (esquema por servicio)
    supabase_ref: str = "yeaylufnjeyiutyxqict"
    supabase_db_password: str = ""
    db_schema: str = "notification"
    log_level: str = "INFO"

    telegram_enabled: bool = True
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    whatsapp_enabled: bool = True
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_recipient: str = ""
    whatsapp_api_version: str = "v20.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
