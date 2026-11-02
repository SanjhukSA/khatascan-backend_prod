from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # stray vars in .env won't crash startup
    )

    # ── CORS ─────────────────────────────────────────────────────────
    allowed_origins: str = "*"

    
    api_key: str = ""

    # ── Gemini (OCR) ─────────────────────────────────────────────────
    gemini_api_key: str
    gemini_model: str = "gemini-3.6-flash"

    # ── PostgreSQL ───────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/receipts"
    auto_create_tables: bool = False

    app_timezone: str = "Asia/Kolkata"

    upload_dir: str = "uploads"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    pending_upload_ttl_hours: int = 24
    cleanup_interval_minutes: int = 60

    @property
    def sqlalchemy_url(self) -> str:
        """DATABASE_URL with an explicit driver. Newer SQLAlchemy versions treat a bare
        'postgresql://' as psycopg v3, but requirements.txt installs psycopg2."""
        url = self.database_url
        if url.startswith("postgres://"):          
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url


settings = Settings()