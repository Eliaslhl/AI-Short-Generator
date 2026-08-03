"""Periodic retention sweep for data/clips and data/videos (audit P1-4):
neither directory was ever purged automatically, so storage grew unbounded.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import backend.scripts.cleanup_old_media as cleanup
from backend.config import settings
from backend.database import Base
from backend.models.user import Job, User

NOW = datetime.now(timezone.utc)
OLD = NOW - timedelta(days=200)
RECENT = NOW - timedelta(hours=1)  # well under the 24h orphaned-download threshold


@pytest.fixture
def cleanup_env(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'cleanup.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    monkeypatch.setattr(cleanup, "AsyncSessionLocal", session_factory)

    clips_root = tmp_path / "clips"
    video_root = tmp_path / "videos"
    temp_root = tmp_path / "tmp"
    clips_root.mkdir()
    video_root.mkdir()
    temp_root.mkdir()
    monkeypatch.setattr(settings, "clips_dir", str(clips_root))
    monkeypatch.setattr(settings, "video_dir", str(video_root))
    monkeypatch.setattr(settings, "video_temp_dir", str(temp_root))
    monkeypatch.setattr(settings, "clips_retention_days", 90)
    monkeypatch.setattr(settings, "orphaned_download_max_age_hours", 24)

    yield SimpleNamespace(
        session_factory=session_factory,
        clips_root=clips_root,
        video_root=video_root,
        temp_root=temp_root,
    )
    asyncio.run(engine.dispose())


def _seed_job(session_factory, job_id, *, status, updated_at):
    async def seed():
        async with session_factory() as db:
            owner = await db.get(User, "cleanup-owner")
            if owner is None:
                owner = User(id="cleanup-owner", email="cleanup@example.com", hashed_password="x")
                db.add(owner)
                await db.flush()
            db.add(Job(
                id=job_id,
                user_id=owner.id,
                youtube_url="https://youtube.com/watch?v=x",
                status=status,
                progress=100 if status == "done" else 0,
                updated_at=updated_at,
            ))
            await db.commit()

    asyncio.run(seed())


def _make_dir_with_file(root, name, *, mtime=None):
    d = root / name
    d.mkdir()
    (d / "content.bin").write_bytes(b"x")
    if mtime is not None:
        ts = mtime.timestamp()
        os.utime(d, (ts, ts))
    return d


def _cutoff():
    return NOW - timedelta(days=settings.clips_retention_days)


def test_sweep_clips_removes_stale_done_and_error_jobs(cleanup_env):
    env = cleanup_env
    _seed_job(env.session_factory, "old-done", status="done", updated_at=OLD)
    _seed_job(env.session_factory, "old-error", status="error", updated_at=OLD)
    _seed_job(env.session_factory, "recent-done", status="done", updated_at=RECENT)
    _seed_job(env.session_factory, "old-processing", status="processing", updated_at=OLD)
    for job_id in ("old-done", "old-error", "recent-done", "old-processing"):
        _make_dir_with_file(env.clips_root, job_id)

    removed = cleanup.sweep_clips(_cutoff(), dry_run=False)

    assert removed == 2
    assert not (env.clips_root / "old-done").exists()
    assert not (env.clips_root / "old-error").exists()
    assert (env.clips_root / "recent-done").exists()
    assert (env.clips_root / "old-processing").exists()


def test_sweep_clips_dry_run_never_deletes(cleanup_env):
    env = cleanup_env
    _seed_job(env.session_factory, "old-done", status="done", updated_at=OLD)
    _make_dir_with_file(env.clips_root, "old-done")

    removed = cleanup.sweep_clips(_cutoff(), dry_run=True)

    assert removed == 1
    assert (env.clips_root / "old-done").exists()


def test_sweep_orphaned_downloads_never_touches_a_processing_job(cleanup_env):
    env = cleanup_env
    _seed_job(env.session_factory, "in-flight", status="processing", updated_at=OLD)
    _make_dir_with_file(env.video_root, "in-flight", mtime=OLD)

    removed = cleanup.sweep_orphaned_downloads(dry_run=False)

    assert removed == 0
    assert (env.video_root / "in-flight").exists()


def test_sweep_orphaned_downloads_removes_old_untracked_directories(cleanup_env):
    env = cleanup_env
    _make_dir_with_file(env.video_root, "no-db-row", mtime=OLD)
    _make_dir_with_file(env.temp_root, "also-orphaned", mtime=OLD)

    removed = cleanup.sweep_orphaned_downloads(dry_run=False)

    assert removed == 2
    assert not (env.video_root / "no-db-row").exists()
    assert not (env.temp_root / "also-orphaned").exists()


def test_sweep_orphaned_downloads_keeps_recent_directories(cleanup_env):
    env = cleanup_env
    _make_dir_with_file(env.video_root, "just-started", mtime=RECENT)

    removed = cleanup.sweep_orphaned_downloads(dry_run=False)

    assert removed == 0
    assert (env.video_root / "just-started").exists()


def test_sweep_orphaned_downloads_removes_a_done_jobs_leftover_download(cleanup_env):
    """A job that finished (and should have cleaned up after itself per the
    P1-3 fix) but crashed before its own cleanup ran must still be swept once
    stale — this is the crash-recovery safety net."""
    env = cleanup_env
    _seed_job(env.session_factory, "crashed-after-done", status="done", updated_at=OLD)
    _make_dir_with_file(env.video_root, "crashed-after-done", mtime=OLD)

    removed = cleanup.sweep_orphaned_downloads(dry_run=False)

    assert removed == 1
    assert not (env.video_root / "crashed-after-done").exists()
