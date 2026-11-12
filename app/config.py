from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # stray vars in .env won't crash startup
    )

    # ── CORS ─────────────────────────────────────────────────────────
    allowed_origins: str = "*"

    # ── Auth ─────────────────────────────────────────────────────────
    # Required: a long random string, e.g. python -c "import secrets; print(secrets.token_urlsafe(48))"
    jwt_secret_key: str
    access_token_expire_minutes: int = 60 * 24 * 7   # 7 days
    bcrypt_rounds: int = 12   # password hashing cost; tests lower it for speed
    # Closed by default. The very first account can always be created (so a fresh
    # install isn't locked out); after that, set ALLOW_REGISTRATION=true to open signup.
    allow_registration: bool = False
    # Signed image links (see /receipts image endpoints) stop working after this long.
    image_url_ttl_seconds: int = 60 * 60

    @field_validator("jwt_secret_key")
    @classmethod
    def _strong_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    # ── Gemini (OCR) ─────────────────────────────────────────────────
    gemini_api_key: str
    gemini_model: str = "gemini-3.6-flash"
    # Tried in order if the main model keeps failing (comma separated). Check these names
    # against Google's current model list: a wrong name is skipped with a warning in the log.
    gemini_fallback_models: str = "gemini-3-flash-preview,gemini-3.5-flash-lite"
    ocr_max_attempts: int = 4   # per model, for 503 / 429 / network errors

    # ── PostgreSQL ───────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/receipts"
    # Dev/test convenience only. In normal use the schema comes from Alembic.
    auto_create_tables: bool = False

    # ── File uploads ─────────────────────────────────────────────────
    # Timezone used for "today" and for bucketing receipts that have no printed date.
    app_timezone: str = "Asia/Kolkata"

    # Max pages (images) in one invoice: caps /upload-many, /process-pages and saving.
    max_pages_per_invoice: int = 10

    upload_dir: str = "uploads"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    # Uploads that were never saved as a receipt are deleted after this long.
    pending_upload_ttl_hours: int = 24
    cleanup_interval_minutes: int = 60

    # ── Rate limits (in-memory, per server process; 0 disables a rule) ──
    trust_proxy_headers: bool = False      # true behind a proxy you control (Render, nginx): use X-Forwarded-For
    login_attempts_per_minute_per_ip: int = 10
    login_failures_per_15min_per_username: int = 8
    register_per_hour_per_ip: int = 10
    upload_files_per_hour: int = 200       # per user
    ocr_pages_per_hour: int = 60           # per user: each page is one Gemini call
    ocr_pages_per_day: int = 300

    @property
    def gemini_fallbacks(self) -> list[str]:
        return [m.strip() for m in self.gemini_fallback_models.split(",") if m.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """DATABASE_URL with an explicit driver. Newer SQLAlchemy versions treat a bare
        'postgresql://' as psycopg v3, but requirements.txt installs psycopg2."""
        url = self.database_url
        if url.startswith("postgres://"):          # older-style URL some hosts hand out
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url


settings = Settings()