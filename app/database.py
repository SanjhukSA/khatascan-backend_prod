from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


_connect_args = (
    {"check_same_thread": False} if settings.sqlalchemy_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.sqlalchemy_url, pool_pre_ping=True, connect_args=_connect_args
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass
