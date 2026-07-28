"""HTTP and queue ownership regression tests for job access controls."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from rq.exceptions import NoSuchJobError
from rq.job import Job as RQJob
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import backend.api.advanced_routes as advanced_routes
import backend.api.routes as routes
from backend.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import Job, User
from backend.services.session_service import session_service
from backend.queue.redis_queue import (
    QueueBackendUnavailableError,
    RedisQueue,
)


class _RQJob:
    def __init__(self, meta: dict | None = None):
        self.meta = meta or {}


class _Queue:
    def __init__(
        self,
        job: _RQJob | None = None,
        error: QueueBackendUnavailableError | None = None,
    ):
        self.job = job
        self.error = error
        self.cancelled = False

    def get_rq_job(self, job_id: str):
        if self.error is not None:
            raise self.error
        return self.job

    def get_job_status(self, job_id: str):
        return {
            "status": "finished",
            "progress": 100,
            "step": "Done",
            "result": {"clips": [{"file": "clip.mp4"}]},
            "error": None,
        }

    def cancel_job(self, job_id: str):
        self.cancelled = True
        return True


class _EnqueuedRQJob:
    def __init__(self):
        self.id = "rq-job"
        self.meta = {}
        self.saved = False

    def save_meta(self):
        self.saved = True


class _RQQueueBackend:
    def __init__(self, job: _EnqueuedRQJob):
        self.job = job

    def enqueue(self, *args, **kwargs):
        return self.job


@pytest.fixture(autouse=True)
def _clear_memory_jobs():
    previous = dict(routes.jobs)
    routes.jobs.clear()
    yield
    routes.jobs.clear()
    routes.jobs.update(previous)


@pytest.fixture
def http_client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    asyncio.run(create_schema())
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, session_factory
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        asyncio.run(engine.dispose())


def _seed_users_and_job(session_factory):
    async def seed():
        owner = User(
            id="user-owner",
            email="owner@example.com",
            hashed_password="not-used-in-test",
            is_active=True,
            is_verified=True,
        )
        other = User(
            id="user-other",
            email="other@example.com",
            hashed_password="not-used-in-test",
            is_active=True,
            is_verified=True,
        )
        job = Job(
            id="job-owner",
            user_id=owner.id,
            youtube_url="https://youtube.com/watch?v=example",
            status="done",
            progress=100,
            video_title="Owner video",
            clips_json=json.dumps([{"file": "/clips/job-owner/clip.mp4"}]),
        )
        async with session_factory() as session:
            session.add_all([owner, other, job])
            await session.commit()

        return {
            "owner_id": owner.id,
            "owner_email": owner.email,
            "other_id": other.id,
            "other_email": other.email,
            "job_id": job.id,
        }

    return asyncio.run(seed())


def _headers(session_factory, user_id: str, _email: str) -> dict[str, str]:
    async def create_session() -> str:
        async with session_factory() as session:
            created = await session_service.create_session(session, user_id)
            await session.commit()
            return created.raw_token

    return {"Cookie": f"{settings.session_cookie_name}={asyncio.run(create_session())}"}


def test_http_owner_can_read_memory_backed_job(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    routes.jobs[data["job_id"]] = {
        "status": "processing",
        "progress": 50,
        "step": "Rendering",
        "clips": [{"file": "/clips/job-owner/clip.mp4"}],
        "video_title": "Owner video",
        "user_id": data["owner_id"],
    }

    clips = client.get(f"/api/clips/{data['job_id']}", headers=owner_headers)
    status = client.get(f"/api/status/{data['job_id']}", headers=owner_headers)

    assert status.status_code == 200
    assert status.json()["status"] == "processing"
    assert clips.status_code == 200
    assert clips.json()["status"] == "processing"


def test_http_owner_falls_back_to_database_when_memory_is_missing(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])

    clips = client.get(f"/api/clips/{data['job_id']}", headers=owner_headers)
    status = client.get(f"/api/status/{data['job_id']}", headers=owner_headers)

    assert status.status_code == 200
    assert status.json()["status"] == "done"
    assert status.json()["progress"] == 100
    assert clips.status_code == 200
    assert clips.json()["video_title"] == "Owner video"


def test_historical_job_error_is_not_exposed_by_status(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    sensitive_error = "postgresql://secret-user:secret-password@private-host/database"

    async def mark_failed():
        async with session_factory() as session:
            job = await session.get(Job, data["job_id"])
            job.status = "error"
            job.error = sensitive_error
            await session.commit()

    asyncio.run(mark_failed())
    response = client.get(f"/api/status/{data['job_id']}", headers=owner_headers)

    assert response.status_code == 200
    assert response.json()["step"] == "Processing failed"
    assert sensitive_error not in response.text


def test_http_foreign_and_missing_jobs_are_indistinguishable(http_client, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    other_headers = _headers(session_factory, data["other_id"], data["other_email"])
    monkeypatch.setattr(routes, "settings", SimpleNamespace(clips_dir=None))

    paths = (
        "/api/status/{job_id}",
        "/api/clips/{job_id}",
    )
    for path_template in paths:
        foreign = client.get(
            path_template.format(job_id=data["job_id"]), headers=other_headers
        )
        missing = client.get(
            path_template.format(job_id="missing-job"), headers=owner_headers
        )

        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json() == {"detail": "Job not found"}


def test_http_anonymous_job_access_uses_project_auth_response(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)

    response = client.get(f"/api/status/{data['job_id']}")

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_http_legacy_download_route_is_not_available(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    other_headers = _headers(session_factory, data["other_id"], data["other_email"])

    for headers in (owner_headers, other_headers, {}):
        response = client.get(f"/api/download-clip/{data['job_id']}/clip.mp4", headers=headers)
        assert response.status_code == 404


def test_http_rq_owner_can_read_and_cancel(http_client, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    queue = _Queue(_RQJob({"user_id": data["owner_id"]}))
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)

    status = client.get("/api/api/status/twitch/rq-job", headers=owner_headers)
    cancelled = client.delete(
        "/api/api/jobs/rq-job", headers={**owner_headers, "Origin": "http://localhost:5173"}
    )

    assert status.status_code == 200
    assert status.json()["status"] == "finished"
    assert cancelled.status_code == 200
    assert cancelled.json() == {"status": "cancelled", "job_id": "rq-job"}
    assert queue.cancelled is True


def test_http_rq_foreign_user_cannot_read_or_cancel(http_client, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    other_headers = _headers(session_factory, data["other_id"], data["other_email"])
    queue = _Queue(_RQJob({"user_id": data["owner_id"]}))
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)

    status = client.get("/api/api/status/twitch/rq-job", headers=other_headers)
    cancelled = client.delete(
        "/api/api/jobs/rq-job", headers={**other_headers, "Origin": "http://localhost:5173"}
    )

    assert status.status_code == 404
    assert cancelled.status_code == 404
    assert status.json() == cancelled.json() == {"detail": "Job not found"}
    assert queue.cancelled is False


@pytest.mark.parametrize(
    "job",
    (
        None,
        _RQJob({}),
        _RQJob({"user_id": 123}),
    ),
)
def test_http_rq_missing_or_invalid_owner_metadata_returns_404(
    http_client, monkeypatch, job
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: _Queue(job))

    response = client.get("/api/api/status/twitch/rq-job", headers=owner_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_http_rq_unavailable_returns_503_for_status_and_cancel(http_client, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    queue = _Queue(error=QueueBackendUnavailableError("Redis unavailable"))
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)

    status = client.get("/api/api/status/twitch/rq-job", headers=owner_headers)
    cancelled = client.delete(
        "/api/api/jobs/rq-job", headers={**owner_headers, "Origin": "http://localhost:5173"}
    )

    assert status.status_code == cancelled.status_code == 503
    assert status.json() == cancelled.json() == {
        "detail": "Job service unavailable"
    }
    assert queue.cancelled is False


def test_rq_fetch_distinguishes_missing_job_from_redis_failure(monkeypatch):
    queue = RedisQueue.__new__(RedisQueue)
    queue.backend = "rq"
    queue.redis_conn = object()

    def missing_job(*args, **kwargs):
        raise NoSuchJobError("missing")

    monkeypatch.setattr(RQJob, "fetch", staticmethod(missing_job))
    assert queue.get_rq_job("missing") is None

    def unavailable(*args, **kwargs):
        raise RedisConnectionError("unavailable")

    monkeypatch.setattr(RQJob, "fetch", staticmethod(unavailable))
    with pytest.raises(QueueBackendUnavailableError):
        queue.get_rq_job("missing")


def test_rq_enqueue_persists_owner_metadata():
    queued_job = _EnqueuedRQJob()
    queue = RedisQueue.__new__(RedisQueue)
    queue.backend = "rq"
    queue.queue = _RQQueueBackend(queued_job)

    queue.enqueue(lambda: None, job_id="rq-job", meta={"user_id": "user-owner"})

    assert queued_job.meta == {"user_id": "user-owner"}
    assert queued_job.saved is True


def test_celery_backend_is_rejected_explicitly():
    queue = RedisQueue.__new__(RedisQueue)
    queue.backend = "celery"

    with pytest.raises(ValueError, match="Only 'rq' is supported"):
        queue._init_backend()
