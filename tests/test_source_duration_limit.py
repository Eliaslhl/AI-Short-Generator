"""A source video longer than settings.max_source_video_duration_seconds must
be rejected before any quota or worker time is spent on it (audit P1-8) —
otherwise a single 10h+ submission can tie up a worker for hours with no
cost control.
"""

import backend.api.routes as routes
from backend.config import settings
from test_subtitle_pipeline import _job_and_quota_snapshot, subtitle_api_client  # noqa: F401
from test_transcription_mode import _authenticate  # noqa: F401

# Captured at collection time, before the autouse conftest fixture (which
# stubs routes._probe_source_duration_seconds for every test by default) runs
# for any test — this is the real implementation, for the two unit tests
# below that exercise it directly.
_real_probe_source_duration_seconds = routes._probe_source_duration_seconds


def test_probe_source_duration_parses_a_successful_yt_dlp_response(monkeypatch):
    class _Proc:
        stdout = '{"duration": 3725.4}'

    import subprocess as real_subprocess

    monkeypatch.setattr(real_subprocess, "run", lambda *_a, **_k: _Proc())

    assert _real_probe_source_duration_seconds("https://youtube.com/watch?v=x") == 3725.4


def test_probe_source_duration_returns_none_on_any_failure(monkeypatch):
    import subprocess as real_subprocess

    def boom(*_a, **_k):
        raise real_subprocess.TimeoutExpired(cmd="yt-dlp", timeout=60)

    monkeypatch.setattr(real_subprocess, "run", boom)

    assert _real_probe_source_duration_seconds("https://youtube.com/watch?v=x") is None


def test_generate_rejects_a_source_video_over_the_duration_limit(subtitle_api_client, monkeypatch):
    client, session_factory = subtitle_api_client
    user = _authenticate(client, session_factory)
    before = _job_and_quota_snapshot(session_factory, user.id)
    pipeline_calls = []
    monkeypatch.setattr(routes, "run_pipeline", lambda *_a, **_k: pipeline_calls.append(1))
    monkeypatch.setattr(
        routes,
        "_probe_source_duration_seconds",
        lambda _url: settings.max_source_video_duration_seconds + 3600,
    )

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=too-long"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 413
    assert "too long" in response.json()["detail"].lower()
    assert pipeline_calls == []
    assert _job_and_quota_snapshot(session_factory, user.id) == before


def test_generate_allows_a_source_video_under_the_duration_limit(subtitle_api_client, monkeypatch):
    client, session_factory = subtitle_api_client
    _authenticate(client, session_factory)
    monkeypatch.setattr(routes, "run_pipeline", lambda *_a, **_k: None)
    monkeypatch.setattr(routes.asyncio, "create_task", lambda task: task)
    monkeypatch.setattr(
        routes, "_probe_source_duration_seconds", lambda _url: 1800.0
    )

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=fine-length"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200


def test_generate_proceeds_when_the_duration_probe_fails(subtitle_api_client, monkeypatch):
    """A probe failure (bad URL, network hiccup) must never block generation
    on its own — the download step is the real, authoritative validator."""
    client, session_factory = subtitle_api_client
    _authenticate(client, session_factory)
    monkeypatch.setattr(routes, "run_pipeline", lambda *_a, **_k: None)
    monkeypatch.setattr(routes.asyncio, "create_task", lambda task: task)
    monkeypatch.setattr(routes, "_probe_source_duration_seconds", lambda _url: None)

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=unknown-length"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
