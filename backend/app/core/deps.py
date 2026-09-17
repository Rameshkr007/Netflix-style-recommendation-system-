"""
Reusable FastAPI dependencies:
  - get_current_user      : decode JWT from Authorization header, load User from DB
  - require_admin         : RBAC guard for admin-only endpoints
  - rate_limiter           : simple sliding-window rate limiter backed by Redis
"""
import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.db_models import User, UserRole
from app.services.cache import get_redis_client

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exception

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action.",
        )
    return user


async def rate_limiter(request: Request) -> None:
    """
    Fixed-window rate limiter: RATE_LIMIT_PER_MINUTE requests per client IP
    per 60-second window, backed by Redis (falls back to allowing the
    request if Redis is unreachable, so a Redis outage doesn't take down
    the whole API).
    """
    client_ip = request.client.host if request.client else "unknown"
    window = int(time.time() // 60)
    key = f"ratelimit:{client_ip}:{window}"

    try:
        redis_client = get_redis_client()
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, 60)
        if current > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
            )
    except HTTPException:
        raise
    except Exception:
        # Redis unavailable -- fail open rather than break the whole API
        return
