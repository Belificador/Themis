from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
