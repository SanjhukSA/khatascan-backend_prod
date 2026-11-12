"""Shared FastAPI dependencies: DB session and the logged-in user."""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.authmanager import decode_access_token
from app.database import SessionLocal
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_db() -> Generator:
    """Yield a SQLAlchemy session, closing it when the request ends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _user_from_token(token: Optional[str], db: Session) -> User:
    user_id = decode_access_token(token) if token else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """The logged-in user, from the `Authorization: Bearer <token>` header."""
    return _user_from_token(token, db)


def get_current_user_allow_query(
    token: Optional[str] = Depends(oauth2_scheme),
    query_token: Optional[str] = Query(None, alias="token", include_in_schema=False),
    db: Session = Depends(get_db),
) -> User:
    """Same, but also accepts ?token=... Used ONLY by the image endpoints, so a plain
    <img src="..."> works (browsers can't add headers to image requests)."""
    return _user_from_token(token or query_token, db)