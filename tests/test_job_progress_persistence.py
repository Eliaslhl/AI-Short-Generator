"""Twitch RQ job progress must reach the DB in real time, not just at the end.

The RQ worker runs in a separate OS process from the web server; nothing but
the database is shared between them. Before this, ProcessingContext.update_progress
only mutated in-memory state, so /api/status/{job_id} reported a flat 0% for
the whole run and jumped straight to 100%/error at the very end.
"""

import asyncio

import pytest

import backend.queue.worker as worker
from backend.models.user import Job
from test_job_authorization import _headers, _seed_users_and_job, http_client


async def _set_job(session_factory, job_id, **fields):
    async with session_factory() as session:
        job = await session.get(Job, job_id)
        for key, value in fields.items():
            setattr(job, key, value)
        await session.commit()


async def _get_job(session_factory, job_id):
    async with session_factory() as session:
        return await session.get(Job, job_id)


def test_persist_job_progress_writes_progress_and_message(http_client, monkeypatch):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    asyncio.run(_set_job(session_factory, data["job_id"], status="processing", progress=0, message=None))

    asyncio.run(worker._persist_job_progress(data["job_id"], 42, "Segmenting video into chunks..."))

    job = asyncio.run(_get_job(session_factory, data["job_id"]))
    assert job.progress == 42
    assert job.message == "Segmenting video into chunks..."


def test_persist_job_progress_never_regresses(http_client, monkeypatch):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    asyncio.run(_set_job(
        session_factory, data["job_id"], status="processing", progress=60, message="Generating clips...",
    ))

    asyncio.run(worker._persist_job_progress(data["job_id"], 30, "a stale/late update"))

    job = asyncio.run(_get_job(session_factory, data["job_id"]))
    assert job.progress == 60
    assert job.message == "Generating clips..."


def test_persist_job_progress_skips_once_job_is_terminal(http_client, monkeypatch):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    asyncio.run(_set_job(session_factory, data["job_id"], status="done", progress=100, message=None))

    asyncio.run(worker._persist_job_progress(data["job_id"], 50, "a late update after completion"))

    job = asyncio.run(_get_job(session_factory, data["job_id"]))
    assert job.status == "done"
    assert job.progress == 100
    assert job.message is None


def test_persist_job_progress_clamps_above_100(http_client, monkeypatch):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    asyncio.run(_set_job(session_factory, data["job_id"], status="processing", progress=0, message=None))

    asyncio.run(worker._persist_job_progress(data["job_id"], 250, "over 100"))

    job = asyncio.run(_get_job(session_factory, data["job_id"]))
    assert job.progress == 100


def test_persist_job_progress_is_best_effort_for_a_missing_job(http_client, monkeypatch):
    _, session_factory = http_client
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)

    # Must not raise even though no such job exists.
    asyncio.run(worker._persist_job_progress("no-such-job", 10, "irrelevant"))


def test_update_progress_persists_through_processing_context(http_client, monkeypatch):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    asyncio.run(_set_job(session_factory, data["job_id"], status="processing", progress=0, message=None))

    ctx = worker.ProcessingContext(data["job_id"], data["owner_id"])
    ctx.update_progress(45, "Analyzing highlights...")

    job = asyncio.run(_get_job(session_factory, data["job_id"]))
    assert job.progress == 45
    assert job.message == "Analyzing highlights..."


def test_status_endpoint_reports_real_progress_when_memory_is_missing(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    asyncio.run(_set_job(
        session_factory, data["job_id"],
        status="processing", progress=37, message="Segmenting video into chunks...",
    ))

    response = client.get(f"/api/status/{data['job_id']}", headers=owner_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processing"
    assert body["progress"] == 37
    assert body["step"] == "Segmenting video into chunks..."


def test_status_endpoint_falls_back_to_status_word_before_first_progress_update(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    asyncio.run(_set_job(session_factory, data["job_id"], status="processing", progress=0, message=None))

    response = client.get(f"/api/status/{data['job_id']}", headers=owner_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["progress"] == 0
    assert body["step"] == "processing"


def test_status_endpoint_does_not_freeze_an_in_progress_job_at_its_first_poll(http_client):
    """A job still processing must never be cached: the RQ worker (a separate
    OS process) keeps advancing it in the DB between polls, and the in-memory
    fast path never re-checks the DB once an entry exists."""
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    asyncio.run(_set_job(
        session_factory, data["job_id"],
        status="processing", progress=10, message="Downloading video from Twitch...",
    ))

    first = client.get(f"/api/status/{data['job_id']}", headers=owner_headers)
    assert first.json()["progress"] == 10

    asyncio.run(_set_job(
        session_factory, data["job_id"],
        status="processing", progress=65, message="Processing chunk 4/6...",
    ))

    second = client.get(f"/api/status/{data['job_id']}", headers=owner_headers)
    assert second.json()["progress"] == 65
    assert second.json()["step"] == "Processing chunk 4/6..."
