"""The YouTube/basic-Twitch pipeline never cleaned up its downloaded source
video, on success or failure — unlike the Twitch advanced/RQ pipeline, which
already isolates and cleans up its download workspace (audit P1-3). A full
copy of potentially copyrighted source content accumulated on disk forever,
once per generation.
"""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

import backend.api.routes as routes
from backend.models.user import Job
from backend.services.transcription_service import TranscriptionMode
from test_subtitle_pipeline import _create_authenticated_user, subtitle_api_client  # noqa: F401


def _seed_processing_job(session_factory, job_id, user_id):
    import asyncio

    async def seed():
        async with session_factory() as db:
            db.add(Job(
                id=job_id,
                user_id=user_id,
                youtube_url="https://youtube.com/watch?v=cleanup-test",
                status="processing",
                progress=0,
            ))
            await db.commit()

    asyncio.run(seed())


def _run_pipeline(job_id, user_id, *, render_clip):
    import asyncio

    segments = [{"start": 0.0, "end": 1.0, "text": "hello", "words": []}]
    routes.jobs[job_id] = {"status": "processing", "progress": 0, "step": "Queued", "clips": []}
    try:
        asyncio.run(
            routes.run_pipeline(
                job_id,
                "https://youtube.com/watch?v=cleanup-test",
                user_id,
                max_clips=1,
                transcription_mode=TranscriptionMode.FAST,
                include_subtitles=False,
            )
        )
    finally:
        routes.jobs.pop(job_id, None)


@pytest.fixture
def download_dir_setup(tmp_path, monkeypatch, subtitle_api_client):
    _client, session_factory = subtitle_api_client
    user, _raw_token = _create_authenticated_user(session_factory)
    job_id = "cleanup-job"
    video_root = tmp_path / "videos"
    monkeypatch.setattr(routes.settings, "video_dir", str(video_root))
    monkeypatch.setattr(routes.settings, "video_temp_dir", str(tmp_path / "unused-temp"))

    import backend.database as database
    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)
    _seed_processing_job(session_factory, job_id, user.id)

    download_dir = video_root / job_id
    download_dir.mkdir(parents=True)
    (download_dir / "source.mp4").write_bytes(b"fake-video-bytes")

    def fake_download_youtube(_url, _job_id):
        return download_dir / "source.mp4", "Source Title"

    monkeypatch.setattr(routes, "download_youtube", fake_download_youtube)
    monkeypatch.setattr(
        "backend.services.transcription_service.transcribe_for_job",
        lambda *_a, **_k: [{"start": 0.0, "end": 1.0, "text": "hello", "words": []}],
    )
    monkeypatch.setattr(routes, "select_top_segments", lambda *_a: [{"start": 0.0, "end": 1.0, "text": "hello"}])
    monkeypatch.setattr(routes, "generate_hook", lambda _text: "Hook")
    monkeypatch.setattr(
        subprocess, "run",
        lambda *_a, **_k: SimpleNamespace(stdout=json.dumps({"format": {"duration": "10"}})),
    )

    return SimpleNamespace(job_id=job_id, user=user, download_dir=download_dir, session_factory=session_factory)


def test_download_dir_is_removed_after_a_successful_job(download_dir_setup, monkeypatch):
    ctx = download_dir_setup
    monkeypatch.setattr(
        routes, "render_clip",
        lambda **_kwargs: {"file": f"/clips/{ctx.job_id}/clip_1.mp4"},
    )

    assert ctx.download_dir.is_dir()
    _run_pipeline(ctx.job_id, ctx.user.id, render_clip=None)

    assert not ctx.download_dir.exists()


def test_download_dir_is_removed_even_when_render_fails(download_dir_setup, monkeypatch):
    ctx = download_dir_setup

    def failing_render_clip(**_kwargs):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(routes, "render_clip", failing_render_clip)

    assert ctx.download_dir.is_dir()
    _run_pipeline(ctx.job_id, ctx.user.id, render_clip=None)

    assert not ctx.download_dir.exists()


def test_cleanup_refuses_a_directory_outside_known_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(routes.settings, "video_dir", str(tmp_path / "videos"))
    monkeypatch.setattr(routes.settings, "video_temp_dir", str(tmp_path / "temp"))
    outside = tmp_path / "elsewhere" / "some-job"
    outside.mkdir(parents=True)
    (outside / "file.txt").write_text("do not delete me")

    routes._cleanup_download_dir(outside, "some-job")

    assert outside.exists()


def test_cleanup_refuses_when_leaf_name_does_not_match_job_id(tmp_path, monkeypatch):
    video_root = tmp_path / "videos"
    monkeypatch.setattr(routes.settings, "video_dir", str(video_root))
    monkeypatch.setattr(routes.settings, "video_temp_dir", str(tmp_path / "temp"))
    mismatched = video_root / "not-the-job-id"
    mismatched.mkdir(parents=True)

    routes._cleanup_download_dir(mismatched, "actual-job-id")

    assert mismatched.exists()


def test_cleanup_removes_a_directory_that_matches_root_and_job_id(tmp_path, monkeypatch):
    video_root = tmp_path / "videos"
    monkeypatch.setattr(routes.settings, "video_dir", str(video_root))
    monkeypatch.setattr(routes.settings, "video_temp_dir", str(tmp_path / "temp"))
    target = video_root / "job-abc"
    target.mkdir(parents=True)
    (target / "video.mp4").write_bytes(b"x")

    routes._cleanup_download_dir(target, "job-abc")

    assert not target.exists()
