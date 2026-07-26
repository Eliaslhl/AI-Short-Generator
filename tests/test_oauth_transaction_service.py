"""One-time OAuth transaction regression tests."""

import asyncio
from datetime import timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base
from backend.services.oauth_transaction_service import (
    consume_oauth_transaction,
    create_oauth_transaction,
)
from backend.services.session_service import utc_now


def test_oauth_state_is_single_use_and_rejects_invalid_values(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'oauth.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def verify():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as db:
            state = await create_oauth_transaction(
                db, provider="google", redirect_uri="http://test/auth/google/callback"
            )
            await db.commit()
            assert await consume_oauth_transaction(
                db, state=state, provider="google", redirect_uri="http://test/auth/google/callback"
            )
            await db.commit()
            assert not await consume_oauth_transaction(
                db, state=state, provider="google", redirect_uri="http://test/auth/google/callback"
            )
            assert not await consume_oauth_transaction(
                db, state="", provider="google", redirect_uri="http://test/auth/google/callback"
            )
            assert not await consume_oauth_transaction(
                db, state="a" * 300, provider="google", redirect_uri="http://test/auth/google/callback"
            )
        await engine.dispose()

    asyncio.run(verify())
