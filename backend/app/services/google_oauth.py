"""
Google OAuth 2.0 Service
-------------------------
Handles Google Sign-In by verifying Google-issued ID tokens.

Flow:
1. Frontend uses Google's JavaScript SDK to get an id_token
2. Frontend sends id_token to POST /api/v1/auth/google
3. This service verifies the token against Google's public keys
4. Extracts user info (email, name, picture) from verified payload
5. Creates user account if first login, otherwise logs in
6. Returns our own JWT token (same as email/password login)

This is production-grade OAuth — no fake implementation.
"""
from __future__ import annotations

import logging

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleOAuthError(Exception):
    """Raised when Google token verification fails."""
    pass


class GoogleOAuthService:

    @staticmethod
    def verify_id_token(token: str) -> dict:
        """
        Verify a Google ID token and return the decoded user payload.

        Args:
            token: The ID token received from the frontend Google Sign-In SDK

        Returns:
            dict with keys: sub, email, name, picture, email_verified

        Raises:
            GoogleOAuthError: If token is invalid, expired, or from wrong client
        """
        if not settings.GOOGLE_CLIENT_ID:
            raise GoogleOAuthError(
                "GOOGLE_CLIENT_ID is not configured. "
                "Add it to your .env file to enable Google Sign-In."
            )

        try:
            # This call verifies:
            # 1. Token signature (against Google's public keys)
            # 2. Token expiry (iat + exp claims)
            # 3. Audience (must match our GOOGLE_CLIENT_ID)
            # 4. Issuer (must be accounts.google.com or accounts.google.com)
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            if not idinfo.get("email_verified"):
                raise GoogleOAuthError("Google account email is not verified.")

            return {
                "sub": idinfo["sub"],              # Unique Google user ID
                "email": idinfo["email"],
                "name": idinfo.get("name", ""),
                "picture": idinfo.get("picture", ""),
                "email_verified": idinfo["email_verified"],
            }

        except ValueError as e:
            # Token verification failed (expired, wrong audience, invalid sig)
            logger.warning("Google token verification failed: %s", e)
            raise GoogleOAuthError(f"Invalid Google token: {e}")
        except Exception as e:
            logger.error("Unexpected error during Google OAuth: %s", e)
            raise GoogleOAuthError(f"Google authentication failed: {e}")
