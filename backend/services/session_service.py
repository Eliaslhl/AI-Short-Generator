"""Opaque, revocable application-session persistence primitives.

This module deliberately does not authenticate HTTP requests or set cookies.
Those integrations belong to later OAuth/session rollout steps.
"""

import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Final

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.models.user import AuthSession, User


DEFAULT_SESSION_TTL: Final = timedelta(days=30)
_TOKEN_BYTES: Final = 32
_MAX_CREATE_ATTEMPTS: Final = 3
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,256}$")
_LOCAL_SESSION_HASH_KEY: Final = "local-development-session-hash-key-not-for-production"
_KNOWN_INSECURE_KEYS: Final = frozenset(
    {
        "change-me",
        "changeme",
        "secret",
        "development-secret",
        "dev-session-hash-key",
        _LOCAL_SESSION_HASH_KEY,
    }
)


class SessionServiceError(RuntimeError):
    """Raised when a session cannot be created after a safe retry."""


class SessionUserUnavailable(ValueError):
    """Raised when a session cannot be created for the requested user."""


@dataclass(frozen=True)
class CreatedSession:
    """The raw token is available only at this creation boundary."""

    session: AuthSession
    raw_token: str = field(repr=False)


def utc_now() -> datetime:
    """Return an aware UTC timestamp so service comparisons stay consistent."""
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite's timezone-naive reads without changing stored values."""
    if not isinstance(value, datetime):
        raise TypeError("now must be a datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _session_hash_key() -> bytes:
    configured = settings.session_hash_key.strip()
    if settings.app_environment == "production":
        normalized = configured.lower()
        if not configured:
            raise RuntimeError("SESSION_HASH_KEY must be configured in production")
        if normalized in _KNOWN_INSECURE_KEYS or "change-me" in normalized:
            raise RuntimeError("SESSION_HASH_KEY uses a known insecure development value")
        if len(configured) < 32:
            raise RuntimeError("SESSION_HASH_KEY must be at least 32 characters in production")
        return configured.encode("utf-8")
    return (configured or _LOCAL_SESSION_HASH_KEY).encode("utf-8")


def hash_session_token(raw_token: str) -> str:
    """Return a deterministic, keyed digest suitable for indexed lookup."""
    if not isinstance(raw_token, str):
        raise TypeError("raw_token must be a string")
    return hmac.new(
        _session_hash_key(), raw_token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _is_well_formed_token(raw_token: object) -> bool:
    return isinstance(raw_token, str) and bool(
        raw_token.strip() and _TOKEN_PATTERN.fullmatch(raw_token)
    )


def _is_token_hash_collision(error: IntegrityError) -> bool:
    """Recognize only the unique constraint that protects token hashes.

    PostgreSQL exposes a constraint name through ``diag``; SQLite exposes the
    qualified column in its error message. A generic unique violation is never
    enough to retry because it may indicate a different data-integrity issue.
    """
    original = error.orig
    diagnostic = getattr(original, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name is not None:
        return constraint_name == "ix_auth_sessions_token_hash"

    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    message = str(original).lower()
    if sqlstate == "23505":
        return (
            "ix_auth_sessions_token_hash" in message
            or "auth_sessions.token_hash" in message
        )
    return "unique constraint failed: auth_sessions.token_hash" in message


class SessionService:
    """Persistence operations for opaque sessions; callers own outer commits."""

    async def create_session(
        self,
        db: AsyncSession,
        user_id: str,
        ttl: timedelta = DEFAULT_SESSION_TTL,
        *,
        now: datetime | None = None,
    ) -> CreatedSession:
        if not isinstance(ttl, timedelta):
            raise TypeError("ttl must be a timedelta")
        if ttl <= timedelta():
            raise ValueError("ttl must be positive")
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            raise SessionUserUnavailable("cannot create a session for the requested user")

        issued_at = _as_utc(utc_now() if now is None else now)
        for _ in range(_MAX_CREATE_ATTEMPTS):
            raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
            session = AuthSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token_hash=hash_session_token(raw_token),
                created_at=issued_at,
                expires_at=issued_at + ttl,
            )
            try:
                async with db.begin_nested():
                    db.add(session)
                    await db.flush()
            except IntegrityError as error:
                if _is_token_hash_collision(error):
                    continue
                raise
            return CreatedSession(session=session, raw_token=raw_token)
        raise SessionServiceError("unable to create a unique session")

    async def get_valid_session(
        self, db: AsyncSession, raw_token: object, *, now: datetime | None = None
    ) -> AuthSession | None:
        if not _is_well_formed_token(raw_token):
            return None
        token_hash = hash_session_token(raw_token)
        result = await db.execute(
            select(AuthSession)
            .options(selectinload(AuthSession.user))
            .where(AuthSession.token_hash == token_hash)
        )
        session = result.scalar_one_or_none()
        if session is None or not hmac.compare_digest(session.token_hash, token_hash):
            return None
        current_time = _as_utc(utc_now() if now is None else now)
        if session.revoked_at is not None or _as_utc(session.expires_at) <= current_time:
            return None
        if session.user is None or not session.user.is_active:
            return None
        return session

    async def touch_session(
        self, db: AsyncSession, session: AuthSession, *, now: datetime | None = None
    ) -> bool:
        current_time = _as_utc(utc_now() if now is None else now)
        result = await db.execute(
            update(AuthSession)
            .where(
                AuthSession.id == session.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > current_time,
            )
            .values(last_seen_at=current_time)
            .execution_options(synchronize_session=False)
        )
        await db.flush()
        return bool(result.rowcount)

    async def revoke_session(
        self, db: AsyncSession, session_id: str, *, now: datetime | None = None
    ) -> bool:
        result = await db.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=_as_utc(utc_now() if now is None else now))
        )
        await db.flush()
        return bool(result.rowcount)

    async def revoke_session_by_token(
        self, db: AsyncSession, raw_token: str | None, *, now: datetime | None = None
    ) -> bool:
        if not _is_well_formed_token(raw_token):
            return False
        result = await db.execute(
            update(AuthSession)
            .where(
                AuthSession.token_hash == hash_session_token(raw_token),
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=_as_utc(utc_now() if now is None else now))
        )
        await db.flush()
        return bool(result.rowcount)

    async def revoke_all_user_sessions(
        self, db: AsyncSession, user_id: str, *, now: datetime | None = None
    ) -> int:
        result = await db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=_as_utc(utc_now() if now is None else now))
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def cleanup_expired_sessions(
        self, db: AsyncSession, *, batch_size: int = 500, now: datetime | None = None
    ) -> int:
        if isinstance(batch_size, bool) or not isinstance(batch_size, int):
            raise TypeError("batch_size must be a positive integer")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        current_time = _as_utc(utc_now() if now is None else now)
        expired_ids = list(
            (
                await db.scalars(
                    select(AuthSession.id)
                    .where(AuthSession.expires_at <= current_time)
                    .order_by(AuthSession.expires_at)
                    .limit(batch_size)
                )
            ).all()
        )
        if not expired_ids:
            return 0
        result = await db.execute(delete(AuthSession).where(AuthSession.id.in_(expired_ids)))
        await db.flush()
        return int(result.rowcount or 0)


session_service = SessionService()
