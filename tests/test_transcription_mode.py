"""HTTP and service regression coverage for strict transcription modes."""

import asyncio

import pytest
from pydantic import ValidationError
from sqlalchemy import select

import backend.api.routes as routes
import backend.database as database
import backend.services.transcription_service as transcription_service
from backend.models.user import Plan, User
from backend.services.transcription_service import TranscriptionMode
from test_subtitle_pipeline import (
    _create_authenticated_user,
    _install_pipeline_mocks,
    _job_and_quota_snapshot,
    subtitle_api_client,
)


def _authenticate(client, session_factory):
    user, raw_token = _create_authenticated_user(session_factory)
    client.cookies.set(routes.settings.session_cookie_name, raw_token)
    return user


async def _set_youtube_plan(session_factory, user_id, plan):
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        user.plan_youtube = plan
        await session.commit()


@pytest.mark.parametrize(
    "payload, expected",
    [({}, None), ({"transcription_mode": None}, None), ({"transcription_mode": "fast"}, TranscriptionMode.FAST), ({"transcription_mode": "quality"}, TranscriptionMode.QUALITY)],
)
def test_generate_request_accepts_only_canonical_transcription_modes(payload, expected):
    request = routes.GenerateRequest(
        youtube_url="https://youtube.com/watch?v=mode-test", **payload
    )

    assert request.transcription_mode is expected


@pytest.mark.parametrize(
    "value",
    ["FAST", "QUALITY", "", " ", " fast", "fast ", "unknown", 1, True, {}, []],
)
def test_generate_request_rejects_noncanonical_transcription_modes(value):
    with pytest.raises(ValidationError):
        routes.GenerateRequest(
            youtube_url="https://youtube.com/watch?v=mode-test",
            transcription_mode=value,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"transcription_mode": "FAST"},
        {"transcription_mode": "QUALITY"},
        {"transcription_mode": ""},
        {"transcription_mode": " "},
        {"transcription_mode": " fast"},
        {"transcription_mode": "unknown"},
        {"transcription_mode": 1},
        {"transcription_mode": True},
        {"transcription_mode": {}},
        {"transcription_mode": []},
    ],
)
def test_invalid_mode_is_rejected_before_generation_side_effects(
    subtitle_api_client, monkeypatch, payload
):
    client, session_factory = subtitle_api_client
    user = _authenticate(client, session_factory)
    before = _job_and_quota_snapshot(session_factory, user.id)
    pipeline_calls = []

    monkeypatch.setattr(routes, "run_pipeline", lambda *_args, **_kwargs: pipeline_calls.append((_args, _kwargs)))

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=mode-test", **payload},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 422
    assert _job_and_quota_snapshot(session_factory, user.id) == before
    assert pipeline_calls == []


@pytest.mark.parametrize("payload", [{}, {"transcription_mode": None}])
def test_absent_or_null_mode_schedules_historical_fast_mode(
    subtitle_api_client, monkeypatch, payload
):
    client, session_factory = subtitle_api_client
    _authenticate(client, session_factory)
    pipeline_calls = []

    monkeypatch.setattr(
        routes,
        "run_pipeline",
        lambda *_args, **_kwargs: pipeline_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(routes.asyncio, "create_task", lambda task: task)

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=mode-test", **payload},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert pipeline_calls[0][1]["transcription_mode"] is None
    assert pipeline_calls[0][1]["include_subtitles"] is None


def test_quality_requires_proplus_before_generation_side_effects(
    subtitle_api_client, monkeypatch
):
    client, session_factory = subtitle_api_client
    user = _authenticate(client, session_factory)
    before = _job_and_quota_snapshot(session_factory, user.id)
    pipeline_calls = []
    monkeypatch.setattr(routes, "run_pipeline", lambda *_args, **_kwargs: pipeline_calls.append((_args, _kwargs)))

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=mode-test", "transcription_mode": "quality"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 403
    assert _job_and_quota_snapshot(session_factory, user.id) == before
    assert pipeline_calls == []


def test_proplus_quality_is_propagated_to_the_pipeline(
    subtitle_api_client, monkeypatch
):
    client, session_factory = subtitle_api_client
    user = _authenticate(client, session_factory)
    asyncio.run(_set_youtube_plan(session_factory, user.id, Plan.PROPLUS))
    pipeline_calls = []

    monkeypatch.setattr(
        routes,
        "run_pipeline",
        lambda *_args, **_kwargs: pipeline_calls.append((_args, _kwargs)),
    )
    monkeypatch.setattr(routes.asyncio, "create_task", lambda task: task)

    response = client.post(
        "/api/generate",
        json={"youtube_url": "https://youtube.com/watch?v=mode-test", "transcription_mode": "quality"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert pipeline_calls[0][1]["transcription_mode"] is TranscriptionMode.QUALITY


def test_transcription_service_selects_explicit_modes(monkeypatch):
    calls = []
    monkeypatch.setattr(
        transcription_service,
        "transcribe_fast_full",
        lambda *_args, **_kwargs: calls.append("fast") or ["fast"],
    )
    monkeypatch.setattr(
        transcription_service,
        "transcribe_two_pass",
        lambda *_args, **_kwargs: calls.append("quality") or ["quality"],
    )

    assert transcription_service.transcribe_for_job("source.mp4") == ["fast"]
    assert transcription_service.transcribe_for_job("source.mp4", TranscriptionMode.FAST) == ["fast"]
    assert transcription_service.transcribe_for_job("source.mp4", TranscriptionMode.QUALITY) == ["quality"]
    assert calls == ["fast", "fast", "quality"]


@pytest.mark.parametrize("invalid_mode", ["FAST", "", False, 0, [], {}])
def test_transcription_service_rejects_unknown_mode_without_fallback(
    monkeypatch, invalid_mode
):
    calls = []
    monkeypatch.setattr(
        transcription_service,
        "transcribe_fast_full",
        lambda *_args, **_kwargs: calls.append("fast"),
    )
    monkeypatch.setattr(
        transcription_service,
        "transcribe_two_pass",
        lambda *_args, **_kwargs: calls.append("quality"),
    )

    with pytest.raises(ValueError, match="Unsupported transcription mode"):
        transcription_service.transcribe_for_job("source.mp4", invalid_mode)

    assert calls == []


@pytest.mark.parametrize("invalid_mode", ["", False, 0, [], {}])
def test_pipeline_rejects_falsy_invalid_modes_before_download(monkeypatch, invalid_mode):
    class _NoJobResult:
        def scalar_one_or_none(self):
            return None

    class _NoJobSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def execute(self, _statement):
            return _NoJobResult()

    job_id = "invalid-mode-pipeline"
    download_calls = []
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: _NoJobSession())
    monkeypatch.setattr(
        routes,
        "download_youtube",
        lambda *_args, **_kwargs: download_calls.append(True),
    )
    routes.jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "step": "Queued",
        "clips": [],
    }
    try:
        asyncio.run(
            routes.run_pipeline(
                job_id,
                "https://youtube.com/watch?v=mode-test",
                "user-id",
                transcription_mode=invalid_mode,
            )
        )
    finally:
        job = routes.jobs.pop(job_id)

    assert download_calls == []
    assert job["status"] == "error"
    assert job["step"] == "Processing failed"


def test_pipeline_forwards_canonical_fast_mode_to_transcription_service(monkeypatch):
    job_id = "mode-pipeline"
    segments = [{"start": 0.0, "end": 1.0, "text": "Hello", "words": []}]
    rendered_segments = []
    _install_pipeline_mocks(monkeypatch, job_id, segments, rendered_segments)
    transcription_calls = []
    monkeypatch.setattr(
        transcription_service,
        "transcribe_for_job",
        lambda *_args, **_kwargs: transcription_calls.append((_args, _kwargs))
        or segments,
    )
    routes.jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "step": "Queued",
        "clips": [],
    }
    try:
        asyncio.run(
            routes.run_pipeline(
                job_id,
                "https://youtube.com/watch?v=mode-test",
                "user-id",
                max_clips=1,
                transcription_mode=TranscriptionMode.FAST,
                include_subtitles=False,
            )
        )
    finally:
        routes.jobs.pop(job_id, None)

    assert transcription_calls == [
        (("source.mp4",), {"transcription_mode": TranscriptionMode.FAST, "language": None})
    ]


def test_quality_pipeline_skips_captions_and_uses_detected_title_language(monkeypatch):
    job_id = "quality-without-subtitles"
    segments = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "Hola",
            "words": [{"word": "Hola", "start": 0.0, "end": 0.5}],
            "detected_language": "es",
        }
    ]
    rendered_segments = []
    _install_pipeline_mocks(monkeypatch, job_id, segments, rendered_segments)
    transcription_calls = []
    title_calls = []
    caption_calls = []
    monkeypatch.setattr(
        transcription_service,
        "transcribe_for_job",
        lambda *_args, **_kwargs: transcription_calls.append((_args, _kwargs))
        or segments,
    )
    monkeypatch.setattr(
        routes,
        "generate_title",
        lambda text, *, language: title_calls.append((text, language)) or "Título",
    )
    monkeypatch.setattr(routes, "generate_hashtags", lambda _text: [])
    monkeypatch.setattr(
        routes,
        "build_captions",
        lambda *_args, **_kwargs: caption_calls.append(True),
    )
    routes.jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "step": "Queued",
        "clips": [],
    }
    try:
        asyncio.run(
            routes.run_pipeline(
                job_id,
                "https://youtube.com/watch?v=mode-test",
                "user-id",
                max_clips=1,
                language="pt-BR",
                is_proplus=True,
                transcription_mode=TranscriptionMode.QUALITY,
                include_subtitles=False,
            )
        )
    finally:
        routes.jobs.pop(job_id, None)

    assert transcription_calls == [
        (("source.mp4",), {"transcription_mode": TranscriptionMode.QUALITY, "language": "pt-BR"})
    ]
    assert title_calls == [("Hola", "es")]
    assert caption_calls == []
    assert rendered_segments[0]["words"] == segments[0]["words"]
    assert rendered_segments[0]["captions"] is None
