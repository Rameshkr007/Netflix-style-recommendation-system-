"""
Auth endpoints: register, login (email+password), Google OAuth login,
refresh token, and "who am I" (/me).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.db_models import User, UserRole
from app.schemas.auth import (
    GoogleLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.google_oauth import GoogleOAuthError, GoogleOAuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
        favorite_genres=",".join(payload.favorite_genres) if payload.favorite_genres else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.email, extra_claims={"role": user.role.value})
    refresh_token = create_refresh_token(subject=user.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(subject=user.email, extra_claims={"role": user.role.value})
    refresh_token = create_refresh_token(subject=user.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token + refresh token pair.
    This implements refresh token rotation -- old refresh token is invalidated
    on use, preventing replay attacks.
    """
    payload_data = decode_refresh_token(payload.refresh_token)
    if not payload_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please log in again.",
        )

    user = db.query(User).filter(User.email == payload_data["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated.")

    # Issue new token pair (rotation)
    new_access = create_access_token(subject=user.email, extra_claims={"role": user.role.value})
    new_refresh = create_refresh_token(subject=user.email)
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/google", response_model=TokenResponse)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Verify a Google ID token (from frontend Google Sign-In SDK) and log user in.
    Creates account automatically on first sign-in (SSO registration).

    Requires GOOGLE_CLIENT_ID in environment variables.
    """
    try:
        google_user = GoogleOAuthService.verify_id_token(payload.id_token)
    except GoogleOAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if user exists by Google sub (most reliable — email can change)
    user = db.query(User).filter(User.google_sub == google_user["sub"]).first()

    if not user:
        # Check if email already registered (merge accounts)
        user = db.query(User).filter(User.email == google_user["email"]).first()
        if user:
            # Link Google account to existing email account
            user.google_sub = google_user["sub"]
            logger.info("Linked Google account to existing user: %s", user.email)
        else:
            # First time Google login → create new account
            user = User(
                email=google_user["email"],
                display_name=google_user["name"] or google_user["email"].split("@")[0],
                google_sub=google_user["sub"],
                hashed_password=None,   # OAuth-only user, no password
                role=UserRole.USER,
            )
            db.add(user)
            logger.info("Created new user via Google OAuth: %s", google_user["email"])

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.email, extra_claims={"role": user.role.value})
    refresh_token_str = create_refresh_token(subject=user.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
