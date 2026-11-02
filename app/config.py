from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # stray vars in .env won't crash startup
    )

    # ── CORS ─────────────────────────────────────────────────────────
    allowed_origins: str = "*"

    # ── Gemini (OCR) ─────────────────────────────────────────────────
    gemini_api_key: str
    gemini_model: str = "gemini-3.6-flash"

    # ── PostgreSQL ───────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/receipts"
    # Dev/test convenience only. In normal use the schema comes from Alembic.
    auto_create_tables: bool = False

    # ── File uploads ─────────────────────────────────────────────────
    # Timezone used for "today" and for bucketing receipts that have no printed date.
    app_timezone: str = "Asia/Kolkata"

    upload_dir: str = "uploads"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    # Uploads that were never saved as a receipt are deleted after this long.
    pending_upload_ttl_hours: int = 24
    cleanup_interval_minutes: int = 60

    @property
    def sqlalchemy_url(self) -> str:
        """DATABASE_URL with an explicit driver. Newer SQLAlchemy versions treat a bare
        'postgresql://' as psycopg v3, but requirements.txt installs psycopg2."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url


settings = Settings()