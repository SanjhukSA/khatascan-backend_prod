"""FastAPI entry point: wires routers, CORS, and the background upload cleanup."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import analytics, auth, receipts
from app.cleanup import cleanup_loop
from app.config import settings
from app.database import Base, engine

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("receipts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # Dev/test convenience only; in production the schema comes from Alembic.
    if settings.auto_create_tables:
        import app.models  # noqa: F401  (registers tables on Base.metadata)
        Base.metadata.create_all(bind=engine)

    cleanup_task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="KhataScan API", lifespan=lifespan)

_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=False,        # auth is a Bearer header, not cookies; also required for "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(receipts.router)
app.include_router(analytics.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}