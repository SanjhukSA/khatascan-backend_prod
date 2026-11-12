"""Register, log in, and 'who am I'."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.authmanager import DUMMY_HASH, create_access_token, hash_password, verify_password
from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> schemas.TokenResponse:
    return schemas.TokenResponse(
        access_token=create_access_token(user.id),
        user=schemas.UserOut.model_validate(user),
    )


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(body: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create an account and return a token (so the app can go straight in)."""
    if not settings.allow_registration:
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


@router.post("/login", response_model=schemas.TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Log in with form fields `username` and `password` (application/x-www-form-urlencoded,
    which is also what the Authorize button in /docs sends).
    """
    user = db.query(User).filter(User.username == form.username.strip().lower()).first()
    ok = verify_password(form.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return user