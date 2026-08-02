"""A failed job must refund exactly one quota credit, never two.

run_pipeline's per-clip render failure handler refunds the credit, sets the
job to "error", commits, then re-raises to unwind out of the function. That
exception used to be caught a second time by the outer except block, which
refunded again unconditionally — a real credit-farming exploit (audit P0-2),
not just a theoretical one: repeatedly submitting a video that always fails
to render grew the user's remaining quota without bound.
"""

import asyncio
import subprocess
import json as _json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

import backend.api.routes as routes
import backend.database as database
from backend.models.user import Job, User
from backend.services.transcription_service import TranscriptionMode
from test_subtitle_pipeline import _create_authenticated_user, subtitle_api_client  # noqa: F401


def _seed_processing_job(session_factory, job_id, user_id, *, youtube_generations_month):
    async def seed():
        async with session_factory() as db:
            user = await db.get(User, user_id)
            user.youtube_generations_month = youtube_generations_month
            user.generations_this_month = youtube_generations_month
            db.add(Job(
                id=job_id,
                user_id=user_id,
                youtube_url="https://youtube.com/watch?v=refund-test",
                status="processing",
                progress=0,
            ))
            await db.commit()

    asyncio.run(seed())


def _youtube_usage(session_factory, user_id):
    async def read():
        async with session_factory() as db:
            user = await db.get(User, user_id)
            return user.youtube_generations_month

    return asyncio.run(read())


def test_render_failure_refunds_the_quota_credit_exactly_once(subtitle_api_client, monkeypatch):
    client, session_factory = subtitle_api_client
    user, _raw_token = _create_authenticated_user(session_factory)
    job_id = "refund-once"
    # 5 represents usage already incremented for this job among prior ones
    # this month — the double-refund bug is invisible when starting at 1,
    # since _decrement_platform_usage floors at 0 and won't go negative.
    _seed_processing_job(session_factory, job_id, user.id, youtube_generations_month=5)
    routes.jobs[job_id] = {"status": "processing", "progress": 0, "step": "Queued", "clips": []}
    # run_pipeline's refund/error handling opens fresh sessions via
    # `from backend.database import AsyncSessionLocal` (bypassing FastAPI's
    # get_db DI, which subtitle_api_client already overrides) — redirect the
    # module-level factory too, or the refund lands in the real default DB
    # instead of this test's isolated one.
    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)

    segments = [{"start": 0.0, "end": 1.0, "text": "hello", "words": []}]
    monkeypatch.setattr(routes, "download_youtube", lambda *_args: (Path("source.mp4"), "Source"))
    monkeypatch.setattr(
        "backend.services.transcription_service.transcribe_for_job",
        lambda *_args, **_kwargs: segments,
    )
    monkeypatch.setattr(routes, "select_top_segments", lambda *_args: [dict(s) for s in segments])
    monkeypatch.setattr(routes, "generate_hook", lambda _text: "Hook")
    monkeypatch.setattr(
        subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=_json.dumps({"format": {"duration": "60"}})),
    )

    def failing_render_clip(*_args, **_kwargs):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(routes, "render_clip", failing_render_clip)

    try:
        asyncio.run(
            routes.run_pipeline(
                job_id,
                "https://youtube.com/watch?v=refund-test",
                user.id,
                max_clips=1,
                transcription_mode=TranscriptionMode.FAST,
                include_subtitles=False,
            )
        )
    finally:
        routes.jobs.pop(job_id, None)

    assert _youtube_usage(session_factory, user.id) == 4, (
        "expected exactly one refund (5 -> 4); a double refund would leave 3"
    )

    async def job_status():
        async with session_factory() as db:
            job = await db.get(Job, job_id)
            return job.status, job.error

    assert asyncio.run(job_status()) == ("error", "A clip could not be rendered")
