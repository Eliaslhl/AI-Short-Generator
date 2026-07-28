"""Regression tests for private clip references in API responses."""

import asyncio
import json

from sqlalchemy import select

import backend.api.routes as routes
import backend.api.advanced_routes as advanced_routes
from backend.models.user import Job
from backend.services.private_media_service import public_clip_payloads
from test_job_authorization import _Queue, _RQJob, _headers, _seed_users_and_job, http_client


def _historical_clips(job_id: str) -> list[object]:
    return [
        {
            "file": f"/clips/{job_id}/clip.mp4",
            "path": "/private/tmp/clips/clip.mp4",
            "output_path": "/private/tmp/clips/clip.mp4",
            "url": f"/clips/{job_id}/clip.mp4",
            "poster": f"/clips/{job_id}/clip.webp",
            "title": "A useful title",
            "duration": 12.5,
            "viral_score": 8.7,
            "hashtags": ["#shorts"],
            "hook": "Watch this",
            "start": 3.0,
            "end": 15.5,
        },
        {"file": "clip_02.mp4", "title": "Second clip", "duration": 8.0},
        "clips_root/internal-file.mp4",
    ]


def test_public_clip_payloads_hide_storage_references_and_keep_metadata():
    payloads = public_clip_payloads("job-123", _historical_clips("job-123"))

    assert [payload["index"] for payload in payloads] == [0, 1, 2]
    assert payloads[0] == {
        "title": "A useful title",
        "duration": 12.5,
        "viral_score": 8.7,
        "hashtags": ["#shorts"],
        "hook": "Watch this",
        "start": 3.0,
        "end": 15.5,
        "index": 0,
        "file": "/api/jobs/job-123/clips/0/media",
        "download_url": "/api/jobs/job-123/clips/0/media?download=true",
    }
    assert payloads[1]["file"] == "/api/jobs/job-123/clips/1/media"
    assert payloads[2] == {
        "index": 2,
        "file": "/api/jobs/job-123/clips/2/media",
        "download_url": "/api/jobs/job-123/clips/2/media?download=true",
    }
    assert public_clip_payloads("job-123", "[]") == []
    assert public_clip_payloads("job-123", "not json") == []


def test_job_clip_responses_use_private_urls_for_historical_metadata(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    raw_clips = _historical_clips(data["job_id"])

    async def set_historical_clips():
        async with session_factory() as session:
            job = await session.scalar(select(Job).where(Job.id == data["job_id"]))
            job.clips_json = json.dumps(raw_clips)
            await session.commit()

    asyncio.run(set_historical_clips())
    headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    clips_response = client.get(f"/api/clips/{data['job_id']}", headers=headers)
    status_response = client.get(f"/api/status/{data['job_id']}", headers=headers)

    for response in (clips_response, status_response):
        assert response.status_code == 200
        clips = response.json()["clips"]
        assert [clip["index"] for clip in clips] == [0, 1, 2]
        assert clips[0]["file"] == f"/api/jobs/{data['job_id']}/clips/0/media"
        assert clips[0]["download_url"] == (
            f"/api/jobs/{data['job_id']}/clips/0/media?download=true"
        )
        assert clips[0]["title"] == "A useful title"
        assert clips[0]["hashtags"] == ["#shorts"]
        assert clips[2]["file"] == f"/api/jobs/{data['job_id']}/clips/2/media"
        assert f'"/clips/{data["job_id"]}/' not in response.text
        assert "/private/tmp" not in response.text
        assert "clips_root" not in response.text


def test_history_uses_an_authenticated_job_endpoint_not_public_clips(http_client):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    headers = _headers(session_factory, data["owner_id"], data["owner_email"])

    response = client.get("/api/history", headers=headers)

    assert response.status_code == 200
    entry = response.json()["history"][0]
    assert entry["clips_url"] == f"/api/status/{data['job_id']}"
    assert f'"/clips/{data["job_id"]}"' not in response.text


def test_twitch_status_uses_private_clip_payloads(http_client, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    monkeypatch.setattr(
        advanced_routes,
        "get_queue",
        lambda: _Queue(_RQJob({"user_id": data["owner_id"]})),
    )

    response = client.get(
        "/api/api/status/twitch/rq-job",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 200
    assert response.json()["clips"] == [
        {
            "index": 0,
            "file": "/api/jobs/rq-job/clips/0/media",
            "download_url": "/api/jobs/rq-job/clips/0/media?download=true",
        }
    ]
