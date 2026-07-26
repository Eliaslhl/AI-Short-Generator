"""One-time OAuth transaction state without persisted credential material."""

import secrets
from datetime import timedelta
from typing import Final

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import OAuthTransaction
from backend.services.session_service import hash_session_token, utc_now


OAUTH_STATE_TTL: Final = timedelta(minutes=10)
_MAX_STATE_LENGTH: Final = 256


def generate_state() -> str:
    return secrets.token_urlsafe(32)


async def create_oauth_transaction(db: AsyncSession, *, provider: str, redirect_uri: str) -> str:
    state = generate_state()
    now = utc_now()
    db.add(OAuthTransaction(
        state_hash=hash_session_token(state), provider=provider,
        redirect_uri=redirect_uri, created_at=now, expires_at=now + OAUTH_STATE_TTL,
    ))
    await db.flush()
    return state


async def consume_oauth_transaction(
    db: AsyncSession, *, state: object, provider: str, redirect_uri: str
) -> bool:
    if not isinstance(state, str) or not state or len(state) > _MAX_STATE_LENGTH:
        return False
    now = utc_now()
    result = await db.execute(
        update(OAuthTransaction)
        .where(
            OAuthTransaction.state_hash == hash_session_token(state),
            OAuthTransaction.provider == provider,
            OAuthTransaction.redirect_uri == redirect_uri,
            OAuthTransaction.consumed_at.is_(None),
            OAuthTransaction.expires_at > now,
        )
        .values(consumed_at=now)
    )
    await db.flush()
    return bool(result.rowcount)
