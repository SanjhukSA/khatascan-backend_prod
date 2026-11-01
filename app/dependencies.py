"""Shared FastAPI dependencies — DB session."""

from typing import Generator

from app.database import SessionLocal


def get_db() -> Generator:
    """Yield a SQLAlchemy session, closing it when the request ends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
