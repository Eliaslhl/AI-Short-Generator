"""A job whose worker process crashed mid-run must eventually be marked
failed and refunded, not left "processing" forever with the frontend polling
into the void (audit P1-2).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import backend.scripts.recover_stuck_jobs as recover
from backend.config import settings
from backend.database import Base
from backend.models.user import Job, User

NOW = datetime.now(timezone.utc)
OLD = NOW - timedelta(hours=48)
RECENT = NOW - timedelta(minutes=5)


@pytest.fixture
def recovery_env(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'recover.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    monkeypatch.setattr(recover, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(settings, "stuck_job_max_processing_hours", 6)

    yield SimpleNamespace(session_factory=session_factory)
    asyncio.run(engine.dispose())


def _seed(session_factory, job_id, *, status, updated_at, url="https://youtube.com/watch?v=x",
          youtube_usage=5, twitch_usage=5):
    async def seed():
        async with session_factory() as db:
            owner = await db.get(User, "stuck-owner")
            if owner is None:
                owner = User(
                    id="stuck-owner", email="stuck@example.com", hashed_password="x",
                    youtube_generations_month=youtube_usage, twitch_generations_month=twitch_usage,
                )
                db.add(owner)
                await db.flush()
            db.add(Job(id=job_id, user_id=owner.id, youtube_url=url, status=status, progress=0, updated_at=updated_at))
            await db.commit()
            return owner.id

    return asyncio.run(seed())


def _cutoff():
    return NOW - timedelta(hours=settings.stuck_job_max_processing_hours)


def _job_state(session_factory, job_id):
    async def read():
        async with session_factory() as db:
            job = await db.get(Job, job_id)
            return job.status, job.error

    return asyncio.run(read())


def _usage(session_factory, user_id):
    async def read():
        async with session_factory() as db:
            user = await db.get(User, user_id)
            return user.youtube_generations_month, user.twitch_generations_month

    return asyncio.run(read())


def test_recover_marks_a_stuck_job_as_error_and_refunds(recovery_env):
    env = recovery_env
    owner_id = _seed(env.session_factory, "stuck-1", status="processing", updated_at=OLD)

    ids = asyncio.run(recover._fetch_stuck_job_ids(_cutoff()))
    assert ids == ["stuck-1"]
    recovered = asyncio.run(recover._recover_one("stuck-1", _cutoff(), dry_run=False))

    assert recovered is True
    assert _job_state(env.session_factory, "stuck-1") == ("error", recover.STUCK_JOB_ERROR_MESSAGE)
    assert _usage(env.session_factory, owner_id) == (4, 5)


def test_recover_never_touches_a_recently_updated_job(recovery_env):
    env = recovery_env
    owner_id = _seed(env.session_factory, "healthy-1", status="processing", updated_at=RECENT)

    ids = asyncio.run(recover._fetch_stuck_job_ids(_cutoff()))

    assert ids == []
    assert _job_state(env.session_factory, "healthy-1") == ("processing", None)
    assert _usage(env.session_factory, owner_id) == (5, 5)


@pytest.mark.parametrize("status", ["done", "error"])
def test_recover_never_touches_a_terminal_job(recovery_env, status):
    env = recovery_env
    _seed(env.session_factory, "terminal-1", status=status, updated_at=OLD)

    ids = asyncio.run(recover._fetch_stuck_job_ids(_cutoff()))

    assert ids == []


def test_recover_dry_run_reports_without_modifying_anything(recovery_env):
    env = recovery_env
    owner_id = _seed(env.session_factory, "stuck-dry", status="processing", updated_at=OLD)

    recovered = asyncio.run(recover._recover_one("stuck-dry", _cutoff(), dry_run=True))

    assert recovered is True
    assert _job_state(env.session_factory, "stuck-dry") == ("processing", None)
    assert _usage(env.session_factory, owner_id) == (5, 5)


def test_recover_skips_a_job_that_resumed_between_scan_and_update(recovery_env):
    """Simulates the exact race the conditional UPDATE defends against: the
    job's real pipeline commits a progress update (bumping updated_at) after
    this script's initial scan but before it applies its own update."""
    env = recovery_env
    owner_id = _seed(env.session_factory, "resumed-1", status="processing", updated_at=OLD)
    cutoff = _cutoff()
    ids = asyncio.run(recover._fetch_stuck_job_ids(cutoff))
    assert ids == ["resumed-1"]

    async def resume():
        async with env.session_factory() as db:
            job = await db.get(Job, "resumed-1")
            job.progress = 42
            job.updated_at = NOW  # the real pipeline is alive and just committed
            await db.commit()

    asyncio.run(resume())

    recovered = asyncio.run(recover._recover_one("resumed-1", cutoff, dry_run=False))

    assert recovered is False
    assert _job_state(env.session_factory, "resumed-1") == ("processing", None)
    assert _usage(env.session_factory, owner_id) == (5, 5)


def test_recover_refunds_the_matching_platform_for_a_twitch_url(recovery_env):
    env = recovery_env
    owner_id = _seed(
        env.session_factory, "stuck-twitch", status="processing", updated_at=OLD,
        url="https://www.twitch.tv/videos/123",
    )

    asyncio.run(recover._recover_one("stuck-twitch", _cutoff(), dry_run=False))

    assert _usage(env.session_factory, owner_id) == (5, 4)
