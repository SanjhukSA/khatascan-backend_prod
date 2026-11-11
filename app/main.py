"""FastAPI application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cleanup import cleanup_loop
from app.config import settings
from app.database import Base, engine
from app.routers import analytics, receipts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare the uploads dir and start the orphan-upload cleanup task.

    The database schema is managed by Alembic (`alembic upgrade head`).
    Set AUTO_CREATE_TABLES=true only for quick local experiments.
    """
    os.makedirs(settings.upload_dir, exist_ok=True)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    cleanup_task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()


app = FastAPI(
    title="Receipts Backend",
    description="Receipt scanning, expense tracking, and analytics API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────
# No cookies/auth yet, so credentials stay off ("*" + credentials is invalid in browsers).
# Turn allow_credentials on and list explicit origins when auth is added.
origins = [o.strip() for o in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────
app.include_router(receipts.router)
app.include_router(analytics.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
