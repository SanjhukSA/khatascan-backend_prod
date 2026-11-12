"""Register, log in, and 'who am I'."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.authmanager import DUMMY_HASH, create_access_token, hash_password, verify_password
from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models import User
from app.ratelimit import client_ip, limit_ip, limiter

router = APIRouter(prefix="/auth", tags=["auth"])

_LOGIN_FAILURES = [("login_fail_user", "login_failures_per_15min_per_username", 15 * 60)]


def _token_response(user: User) -> schemas.TokenResponse:
    return schemas.TokenResponse(
        access_token=create_access_token(user.id),
        user=schemas.UserOut.model_validate(user),
    )


@router.post(
    "/register",
    response_model=schemas.TokenResponse,
    status_code=201,
    dependencies=[Depends(limit_ip("register_ip", "register_per_hour_per_ip", 3600))],
)
def register(body: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create an account and return a token (so the app can go straight in).

    Signup is closed unless ALLOW_REGISTRATION=true, except that the very first account
    can always be created."""
    no_users_yet = db.query(User.id).first() is None
    if not (settings.allow_registration or no_users_yet):
        raise HTTPException(status_code=403, detail="Registration is closed.")
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That username is already taken.")
    db.refresh(user)
    return _token_response(user)


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    dependencies=[Depends(limit_ip("login_ip", "login_attempts_per_minute_per_ip", 60))],
)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Log in with form fields `username` and `password` (application/x-www-form-urlencoded,
    which is also what the Authorize button in /docs sends).
    Too many failed attempts for one username (from anywhere) temporarily blocks that username.
    """
    username = form.username.strip().lower()
    limiter.check(username, _LOGIN_FAILURES)

    user = db.query(User).filter(User.username == username).first()
    ok = verify_password(form.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok:
        limiter.record(username, _LOGIN_FAILURES)
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return user
