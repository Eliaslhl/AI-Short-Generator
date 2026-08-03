"""The main /generate quota check now locks the user row before checking and
consuming usage (audit P1-1), mirroring the pattern already used by the
Twitch advanced route. Without it, two concurrent requests could both read
the same pre-increment usage and both pass the check, exceeding the plan's
monthly limit.

Note: SQLAlchemy silently drops FOR UPDATE when compiling for SQLite (no
error, no lock) — confirmed directly: `select(...).with_for_update()`
compiles to a plain SELECT on the sqlite dialect. This test suite therefore
cannot demonstrate the lock actually serializing two concurrent requests
(same limitation the existing Twitch route's equivalent lock has never had a
test for either — it only takes effect on PostgreSQL). What it does verify:
the new locked-read code path preserves exactly the same quota semantics as
before for both the exhausted and under-quota cases, and doesn't silently
skip the check or double-count usage.
"""

import asyncio

import pytest
from sqlalchemy import select

import backend.api.routes as routes
from backend.models.user import User
from test_subtitle_pipeline import _job_and_quota_snapshot, subtitle_api_client  # noqa: F401
from test_transcription_mode import _authenticate  # noqa: F401


def _set_youtube_limit_and_usage(session_factory, user_id, *, limit, usage):
    async def apply():
        async with session_factory() as db:
            user = await db.scalar(select(User).where(User.id == user_id))
            user.youtube_limit_override = limit
            user.youtube_generations_month = usage
            user.generations_this_month = usage
            await db.commit()

    asyncio.run(apply())


def _youtube_usage(session_factory, user_id):
    async def read():
        async with session_factory() as db:
            user = await db.scalar(select(User).where(User.id == user_id))
            return user.youtube_generations_month

    return asyncio.run(read())


def test_generate_still_rejects_when_quota_already_exhausted(subtitle_api_client, monkeypatch):
    client, session_factory = subtitle_api_client
    user = _authenticate(client, session_factory)
    _set_youtube_limit_and_usage(session_factory, user.id, limit=1, usage=1)
    pipeline_calls = []
    monkeypatch.setattr(routes, "run_pipeline", lambda *_args, **_kwargs: pipeline_calls.append(1))
    monkeypatch.setattr(routes.asyncio, "create_task", lambda task: task)

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=quota-race"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 402
    assert response.json()["detail"]["error"] == "quota_exceeded"
    assert pipeline_calls == []
    assert _youtube_usage(session_factory, user.id) == 1


def test_generate_succeeds_and_increments_by_exactly_one_when_under_quota(
    subtitle_api_client, monkeypatch
):
    client, session_factory = subtitle_api_client
    user = _authenticate(client, session_factory)
    _set_youtube_limit_and_usage(session_factory, user.id, limit=3, usage=1)
    monkeypatch.setattr(routes, "run_pipeline", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(routes.asyncio, "create_task", lambda task: task)

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=quota-race-ok"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert _youtube_usage(session_factory, user.id) == 2


def test_generate_locked_read_uses_with_for_update():
    """Guards against an accidental revert: the quota check must read the
    user row through a locking SELECT, not a plain (unlocked) fetch."""
    import inspect

    source = inspect.getsource(routes.generate)
    assert "with_for_update()" in source
