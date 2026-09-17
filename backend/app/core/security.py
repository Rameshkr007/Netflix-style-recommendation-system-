"""
Security utilities: password hashing (bcrypt) and JWT token management.

Access token:  short-lived (24h), used for API authentication
Refresh token: long-lived (30 days), used ONLY to get new access tokens
               Refresh token rotation: each use issues a new refresh token
               and the old one should be considered invalidated.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
import bcrypt

from app.core.config import get_settings

settings = get_settings()
REFRESH_TOKEN_EXPIRE_DAYS = 30


def hash_password(plain_password: str) -> str:
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password cannot exceed 72 bytes.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Short-lived JWT for API requests (24 hours)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """
    Long-lived JWT for token refresh (30 days).
    Stored client-side in httpOnly cookie or secure storage.
    On use: this token is invalidated and a NEW pair is issued (rotation).
    """
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",   # Different type prevents refresh tokens being used as access tokens
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None   # Reject refresh tokens used as access tokens
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None   # Reject access tokens used as refresh tokens
        return payload
    except JWTError:
        return None
