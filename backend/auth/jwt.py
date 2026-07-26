"""
auth/jwt.py – JWT token creation and verification.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from fastapi import HTTPException, status

from backend.config import settings

_configured_secret_key = os.getenv("SECRET_KEY", "")
_KNOWN_INSECURE_SECRETS = {
    "change-me",
    "changeme",
    "secret",
    "development-secret",
    "your-secret-key",
    "your-random-secret-key",
    "dev-secret-key",
    "test-secret-not-for-production",
    "local-development-key-not-for-production",
}


def _validate_production_secret_key(secret_key: str) -> None:
    normalized = secret_key.strip().lower()
    if not normalized:
        raise RuntimeError("SECRET_KEY must be configured in production")
    if normalized in _KNOWN_INSECURE_SECRETS or "change-me" in normalized:
        raise RuntimeError("SECRET_KEY uses a known insecure development value")
    if len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production")


if settings.app_environment == "production":
    _validate_production_secret_key(_configured_secret_key)

SECRET_KEY = _configured_secret_key or "local-development-key-not-for-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises HTTP 401 on failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
