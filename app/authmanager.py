"""Password hashing (bcrypt) and access tokens (JWT)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """bcrypt hash with a random salt. Only the hash is ever stored."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:      # malformed hash, or a password bcrypt refuses (> 72 bytes)
        return False


# Checked when the username doesn't exist, so "unknown user" and "wrong password"
# take the same time and can't be told apart.
DUMMY_HASH = hash_password("not-a-real-password")


def create_access_token(user_id: uuid.UUID, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(minutes=settings.access_token_expire_minutes)
    )
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[uuid.UUID]:
    """The user id inside a valid, unexpired token, else None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None