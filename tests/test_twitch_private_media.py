"""Twitch/RQ clips must use the same private media boundary as normal jobs."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import backend.api.advanced_routes as advanced_routes
import backend.queue.worker as worker
from backend.config import settings
from backend.models.user import Job, User
from test_job_authorization import _Queue, _RQJob, _headers, _seed_users_and_job, http_client


class _FakeClipGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    def generate_from_highlight(self, **_kwargs):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / "twitch-clip.mp4"
        path.write_bytes(b"twitch-private-media")
        return {"mp4": str(path), "webm": None}


class _RecordingQueue:
    def __init__(self):
        self.job_id: str | None = None
        self.meta: dict | None = None

    def enqueue(self, _func, **kwargs):
        self.job_id = kwargs["job_id"]
        self.meta = kwargs["meta"]
        return self.job_id


def test_advanced_twitch_job_is_persisted_with_its_owner(http_client, monkeypatch):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    queue = _RecordingQueue()
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)

    async def create_job():
        async with session_factory() as session:
            owner = await session.get(User, data["owner_id"])
            response = await advanced_routes.generate_twitch_advanced(
                advanced_routes.TwitchAdvancedRequest(url="https://twitch.tv/channel"),
                owner,
                session,
            )
            job = await session.get(Job, response["job_id"])
            return response, job

    response, job = asyncio.run(create_job())

    assert job is not None
    assert job.user_id == data["owner_id"]
    assert job.youtube_url == "https://twitch.tv/channel"
    assert job.status == "pending"
    assert queue.job_id == response["job_id"]
    assert queue.meta == {"user_id": data["owner_id"]}


def test_persisted_twitch_clip_is_served_by_the_private_media_route(
    http_client, tmp_path, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))
    monkeypatch.setattr(
        worker,
        "create_clip_generator",
        lambda output_dir: _FakeClipGenerator(output_dir),
    )
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)

    clips = worker._generate_clips(
        [SimpleNamespace(start_time=1.0, end_time=3.0, score=9.0)],
        "source.mp4",
        data["job_id"],
    )
    asyncio.run(worker._persist_twitch_job_result(data["job_id"], clips, "done", 100))
    monkeypatch.setattr(
        advanced_routes,
        "get_queue",
        lambda: _Queue(_RQJob({"user_id": data["owner_id"]})),
    )
    headers = _headers(session_factory, data["owner_id"], data["owner_email"])

    status = client.get(f"/api/api/status/twitch/{data['job_id']}", headers=headers)
    media = client.get(status.json()["clips"][0]["file"], headers=headers)

    assert clips[0]["file"] == "twitch-clip.mp4"
    assert (tmp_path / data["job_id"] / "twitch-clip.mp4").is_file()
    assert status.status_code == 200
    assert status.json()["clips"][0]["file"] == (
        f"/api/jobs/{data['job_id']}/clips/0/media"
    )
    assert media.status_code == 200
    assert media.content == b"twitch-private-media"
