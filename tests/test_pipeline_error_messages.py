"""run_pipeline's failure handler used to overwrite every error with the
same fixed "Processing failed" string, discarding whatever detail was
actually raised (private video, removed video, age-restricted, bot-check,
Twitch access-denied, etc.) — audit P1-7. Users saw the same unhelpful
message for every failure, which drove support tickets.

_classify_pipeline_error() fixes this narrowly: only a small set of known,
already-safe failure signatures (matching the categorized RuntimeError
prefixes youtube_service.py / twitch_service.py already raise) get a clear
message. Anything else keeps the original generic fallback — this must never
start echoing raw exception text, which can contain yt-dlp's raw stderr or
operator-facing setup instructions.
"""

import asyncio
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.api.routes as routes
import backend.database as database
from backend.models.user import Job
from backend.services.transcription_service import TranscriptionMode
from test_subtitle_pipeline import _create_authenticated_user, subtitle_api_client  # noqa: F401


@pytest.mark.parametrize(
    "raw_exception_text,expected",
    [
        ("Video not available: This video is not available", "This video is not available (it may be private, removed, or region-restricted)."),
        ("Access denied (login may be required): HTTP Error 403", "This video requires the uploader's permission and cannot be accessed."),
        ("Video not found: HTTP Error 404", "This video is unavailable or has been removed."),
        ("yt-dlp failed (exit 1): ERROR: [youtube] zzzzzzzzzzz: Video unavailable", "This video is unavailable or has been removed."),
        ("ERROR: This video is no longer available because the uploader has closed their account", "This video is unavailable or has been removed."),
        ("ERROR: Sign in to confirm your age. This video may be inappropriate for some users.", "This video is age-restricted and cannot be processed."),
        ("yt-dlp failed after bot-check fallbacks (...) and auto-refresh failed: (...)", "The video platform temporarily blocked this download as suspicious traffic. Please try again later."),
        ("ERROR: [youtube] abc123: Sign in to confirm you're not a bot", "The video platform temporarily blocked this download as suspicious traffic. Please try again later."),
        ("Download timeout after 5 minutes: Command timed out", "The download took too long and timed out. Please try again."),
    ],
)
def test_classify_known_failure_signatures(raw_exception_text, expected):
    assert routes._classify_pipeline_error(RuntimeError(raw_exception_text)) == expected


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "postgresql://secret-user:secret-password@private-host/database connection refused",
        "FileNotFoundError: /Users/eliaslahlouh/secret-project/data/videos/abc/source.mp4",
        "something completely unrelated went wrong in ffmpeg",
        "",
    ],
)
def test_classify_falls_back_to_generic_message_for_anything_unrecognized(unsafe_text):
    """The safety property this whole function exists to preserve: never
    echo exception text that wasn't explicitly allow-listed above."""
    message = routes._classify_pipeline_error(RuntimeError(unsafe_text))

    assert message == "Processing failed"
    assert "secret" not in message
    assert "postgresql://" not in message
    assert "/Users/" not in message


def test_run_pipeline_surfaces_a_classified_message_on_download_failure(subtitle_api_client, monkeypatch):
    client, session_factory = subtitle_api_client
    user, _raw_token = _create_authenticated_user(session_factory)
    job_id = "classify-download-fail"
    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)

    async def seed():
        async with session_factory() as db:
            db.add(Job(id=job_id, user_id=user.id, youtube_url="https://youtube.com/watch?v=x", status="processing", progress=0))
            await db.commit()

    asyncio.run(seed())

    def failing_download(_url, _job_id):
        raise RuntimeError("Video not found: HTTP Error 404: Not Found")

    monkeypatch.setattr(routes, "download_youtube", failing_download)
    routes.jobs[job_id] = {"status": "processing", "progress": 0, "step": "Queued", "clips": []}
    try:
        asyncio.run(
            routes.run_pipeline(
                job_id, "https://youtube.com/watch?v=x", user.id,
                max_clips=1, transcription_mode=TranscriptionMode.FAST, include_subtitles=False,
            )
        )
        in_memory_step = routes.jobs[job_id]["step"]
    finally:
        routes.jobs.pop(job_id, None)

    assert in_memory_step == "This video is unavailable or has been removed."

    async def read_job():
        async with session_factory() as db:
            return await db.get(Job, job_id)

    job = asyncio.run(read_job())
    assert job.status == "error"
    assert job.error == "This video is unavailable or has been removed."
    assert job.message == "This video is unavailable or has been removed."


def test_run_pipeline_falls_back_to_generic_message_for_an_unrecognized_failure(subtitle_api_client, monkeypatch):
    client, session_factory = subtitle_api_client
    user, _raw_token = _create_authenticated_user(session_factory)
    job_id = "classify-unknown-fail"
    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)

    async def seed():
        async with session_factory() as db:
            db.add(Job(id=job_id, user_id=user.id, youtube_url="https://youtube.com/watch?v=x", status="processing", progress=0))
            await db.commit()

    asyncio.run(seed())

    def failing_download(_url, _job_id):
        raise RuntimeError("postgresql://secret:pw@host/db unreachable")

    monkeypatch.setattr(routes, "download_youtube", failing_download)
    routes.jobs[job_id] = {"status": "processing", "progress": 0, "step": "Queued", "clips": []}
    try:
        asyncio.run(
            routes.run_pipeline(
                job_id, "https://youtube.com/watch?v=x", user.id,
                max_clips=1, transcription_mode=TranscriptionMode.FAST, include_subtitles=False,
            )
        )
    finally:
        routes.jobs.pop(job_id, None)

    async def read_job():
        async with session_factory() as db:
            return await db.get(Job, job_id)

    job = asyncio.run(read_job())
    assert job.error == "Processing failed"
    assert "secret" not in job.error
