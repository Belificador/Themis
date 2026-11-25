from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


class Settings(BaseSettings):
    service_name: str = "themis-app"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    media_dir: str = "./media"
    image_max_bytes: int = 5 * 1024 * 1024
    invoice_max_bytes: int = 10 * 1024 * 1024
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket_product_images: str = "product-images"
    supabase_bucket_invoices: str = "sales-invoices"
    supabase_ref: str = "yeaylufnjeyiutyxqict"
    supabase_db_password: str = ""
    db_schema: str = "themis"
    log_level: str = "INFO"
    dedupe_window_seconds: int = 0
    # Tasas BCV (dolarapi.com, sin clave).
    bcv_api_url: str = "https://ve.dolarapi.com/v1/dolares"
    bcv_cache_seconds: int = 3600
    # Orígenes permitidos (coma-separados) para el frontend desplegado aparte.
    cors_origins: str = ""
    # Regex opcional, p. ej. https://.*\.vercel\.app para previews.
    cors_origin_regex: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def now_venezuela(self) -> datetime:
        """Retorna la fecha y hora actual en zona horaria de Venezuela."""
        return datetime.now(VENEZUELA_TZ)


settings = Settings()

# Zona horaria de Venezuela (America/Caracas = UTC-4, sin cambio de horario de verano)
VENEZUELA_TZ = ZoneInfo("America/Caracas")

def now_venezuela() -> datetime:
    """Retorna la fecha y hora actual en zona horaria de Venezuela."""
    return settings.now_venezuela()
