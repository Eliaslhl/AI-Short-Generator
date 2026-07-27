"""Regression coverage for configurable subtitle generation."""

import asyncio
import json
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import backend.api.routes as routes
import backend.database as database
import backend.video.video_editor as video_editor
from backend.config import Settings, settings
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import Job, User
from backend.api.routes import GenerateRequest
from backend.services.session_service import session_service


def _request_payload(**overrides):
    return {"youtube_url": "https://www.youtube.com/watch?v=test", **overrides}


@pytest.mark.parametrize(
    ("value", "expected"),
    [({}, None), ({"include_subtitles": None}, None), ({"include_subtitles": True}, True), ({"include_subtitles": False}, False)],
)
def test_generate_request_accepts_only_nullable_json_booleans(value, expected):
    assert GenerateRequest(**_request_payload(**value)).include_subtitles is expected


@pytest.mark.parametrize("value", ["true", "false", 1, 0, "not-a-bool"])
def test_generate_request_rejects_non_boolean_subtitle_values(value):
    with pytest.raises(ValidationError):
        GenerateRequest(**_request_payload(include_subtitles=value))


def test_subtitle_configuration_defaults_to_true(monkeypatch):
    monkeypatch.delenv("INCLUDE_SUBTITLES_BY_DEFAULT", raising=False)
    assert Settings(_env_file=None).include_subtitles_by_default is True


@pytest.mark.parametrize(("value", "expected"), [("true", True), ("false", False)])
def test_subtitle_configuration_reads_boolean_environment_values(monkeypatch, value, expected):
    monkeypatch.setenv("INCLUDE_SUBTITLES_BY_DEFAULT", value)
    assert Settings(_env_file=None).include_subtitles_by_default is expected


def test_subtitle_configuration_rejects_invalid_environment_value(monkeypatch):
    monkeypatch.setenv("INCLUDE_SUBTITLES_BY_DEFAULT", "invalid")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.fixture
def subtitle_api_client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'subtitle-api.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    asyncio.run(create_schema())
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, session_factory
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        asyncio.run(engine.dispose())


def _create_authenticated_user(session_factory):
    async def create_user_and_session():
        async with session_factory() as db:
            user = User(
                id="subtitle-api-user",
                email="subtitle-api@example.com",
                hashed_password="not-used",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            session = await session_service.create_session(db, user.id)
            await db.commit()
            return user, session.raw_token

    return asyncio.run(create_user_and_session())


def _job_and_quota_snapshot(session_factory, user_id):
    async def snapshot():
        async with session_factory() as db:
            jobs = await db.scalar(
                select(func.count()).select_from(Job).where(Job.user_id == user_id)
            )
            user = await db.get(User, user_id)
            return jobs, (
                user.youtube_generations_month,
                user.twitch_generations_month,
                user.generations_this_month,
            )

    return asyncio.run(snapshot())


@pytest.mark.parametrize("invalid_value", ["true", 1])
def test_invalid_subtitle_values_are_rejected_before_generation_side_effects(
    subtitle_api_client,
    monkeypatch,
    invalid_value,
):
    client, session_factory = subtitle_api_client
    user, raw_token = _create_authenticated_user(session_factory)
    client.cookies.set(settings.session_cookie_name, raw_token)
    before = _job_and_quota_snapshot(session_factory, user.id)
    pipeline_calls = []
    external_calls = []

    def fake_run_pipeline(*args, **kwargs):
        pipeline_calls.append((args, kwargs))

    def external_service(*args, **kwargs):
        external_calls.append((args, kwargs))
        raise AssertionError("generation services must not run for invalid input")

    monkeypatch.setattr(routes, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(routes, "download_youtube", external_service)
    monkeypatch.setattr(routes, "download_twitch", external_service)
    monkeypatch.setattr(
        "backend.services.transcription_service.transcribe_for_job",
        external_service,
    )
    monkeypatch.setattr(routes, "render_clip", external_service)

    response = client.post(
        "/api/generate",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=subtitle-test",
            "include_subtitles": invalid_value,
        },
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 422
    assert _job_and_quota_snapshot(session_factory, user.id) == before
    assert pipeline_calls == []
    assert external_calls == []


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _PipelineSession:
    def __init__(self, job_record):
        self.job_record = job_record
        self.commit_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, _statement):
        return _Result(self.job_record)

    async def commit(self):
        self.commit_count += 1


def _install_pipeline_mocks(monkeypatch, job_id, segments, rendered_segments):
    job_record = SimpleNamespace(
        id=job_id,
        status="pending",
        progress=0,
        clips_json=None,
        video_title=None,
        error=None,
    )
    session = _PipelineSession(job_record)
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(routes, "download_youtube", lambda *_args: (Path("source.mp4"), "Source"))
    monkeypatch.setattr(
        "backend.services.transcription_service.transcribe_for_job",
        lambda *_args: segments,
    )
    monkeypatch.setattr(routes, "select_top_segments", lambda *_args: [dict(segment) for segment in segments])
    monkeypatch.setattr(routes, "generate_hook", lambda _text: "Hook")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=json.dumps({"format": {"duration": "60"}})),
    )

    def fake_render_clip(*, segment, **_kwargs):
        rendered_segments.append(dict(segment))
        return {"file": f"/clips/{job_id}/clip_{len(rendered_segments)}.mp4"}

    monkeypatch.setattr(routes, "render_clip", fake_render_clip)
    return job_record


@pytest.mark.parametrize(
    ("include_subtitles", "configured_default", "expected_caption_calls"),
    [(True, False, 2), (False, True, 0), (None, True, 2), (None, False, 0)],
)
def test_pipeline_builds_captions_only_when_enabled(
    monkeypatch,
    include_subtitles,
    configured_default,
    expected_caption_calls,
):
    job_id = f"subtitle-{include_subtitles}-{configured_default}".replace(" ", "")
    segments = [
        {"start": 0.0, "end": 10.0, "text": "first segment", "words": [{"word": "first", "start": 0.0, "end": 0.5}]},
        {"start": 10.0, "end": 20.0, "text": "second segment", "words": [{"word": "second", "start": 10.0, "end": 10.5}]},
    ]
    rendered_segments = []
    job_record = _install_pipeline_mocks(monkeypatch, job_id, segments, rendered_segments)
    monkeypatch.setattr(settings, "include_subtitles_by_default", configured_default)
    caption_calls = []

    def fake_build_captions(text, words):
        caption_calls.append((text, words))
        return [{"text": text, "start": words[0]["start"], "end": words[0]["end"]}]

    monkeypatch.setattr(routes, "build_captions", fake_build_captions)
    routes.jobs[job_id] = {"status": "pending", "progress": 0, "step": "Queued", "clips": []}
    try:
        asyncio.run(
            routes.run_pipeline(
                job_id,
                "https://www.youtube.com/watch?v=test",
                "user-id",
                max_clips=2,
                include_subtitles=include_subtitles,
            )
        )
    finally:
        routes.jobs.pop(job_id, None)

    assert len(caption_calls) == expected_caption_calls
    assert len(rendered_segments) == 2
    assert all(segment["words"] for segment in rendered_segments)
    if expected_caption_calls:
        assert all(segment["captions"] for segment in rendered_segments)
    else:
        assert all(segment["captions"] is None for segment in rendered_segments)
    assert json.loads(job_record.clips_json) == [
        {"file": f"/clips/{job_id}/clip_1.mp4"},
        {"file": f"/clips/{job_id}/clip_2.mp4"},
    ]


def _fake_ffmpeg_run(commands):
    def run(command, **_kwargs):
        commands.append(command)
        output = Path(command[-1])
        if output.suffix in {".ass", ".mp4"}:
            output.write_bytes(b"output")
        return SimpleNamespace(stdout="", stderr="")

    return run


@pytest.mark.parametrize("captions", [None, []], ids=["none", "empty-list"])
def test_ffmpeg_without_captions_skips_subtitle_artifacts(
    monkeypatch,
    tmp_path,
    captions,
):
    commands = []
    monkeypatch.setattr(subprocess, "run", _fake_ffmpeg_run(commands))
    monkeypatch.setattr(video_editor, "_write_srt", lambda *_args: pytest.fail("SRT must not be written"))

    assert video_editor._render_with_ffmpeg(
        "source.mp4",
        0.0,
        5.0,
        tmp_path / "output.mp4",
        None,
        captions,
        "default",
        None,
    )
    assert all("subtitles=" not in " ".join(command) for command in commands)


def test_ffmpeg_with_captions_preserves_subtitle_path(monkeypatch, tmp_path):
    commands = []
    original_write_srt = video_editor._write_srt
    write_calls = []

    def record_write_srt(*args):
        write_calls.append(args)
        return original_write_srt(*args)

    monkeypatch.setattr(subprocess, "run", _fake_ffmpeg_run(commands))
    monkeypatch.setattr(video_editor, "_write_srt", record_write_srt)
    captions = [{"text": "caption", "start": 0.0, "end": 1.0}]

    assert video_editor._render_with_ffmpeg(
        "source.mp4", 0.0, 5.0, tmp_path / "output.mp4", None, captions, "default", None
    )
    assert len(write_calls) == 1
    assert any("subtitles=filename=" in " ".join(command) for command in commands)


class _FakeMovieClip:
    duration = 5.0

    def subclipped(self, *_args):
        return self

    def write_videofile(self, *_args, **_kwargs):
        return None

    def close(self):
        return None


def _install_moviepy_fallback(monkeypatch, tmp_path):
    module = types.ModuleType("moviepy")
    module.VideoFileClip = lambda _path: _FakeMovieClip()
    monkeypatch.setitem(sys.modules, "moviepy", module)
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))
    monkeypatch.setattr(video_editor, "_render_with_ffmpeg", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(video_editor, "_crop_to_portrait", lambda clip: clip)
    monkeypatch.setattr(video_editor, "_create_thumbnail", lambda *_args: None)


def test_moviepy_fallback_without_captions_skips_caption_overlay(monkeypatch, tmp_path):
    _install_moviepy_fallback(monkeypatch, tmp_path)
    monkeypatch.setattr(
        video_editor,
        "_add_caption_overlays",
        lambda *_args: pytest.fail("caption overlay must not be created"),
    )

    result = video_editor.render_clip(
        "source.mp4", {"start": 0.0, "end": 5.0, "captions": None}, "job", 0
    )
    assert result["file"] == "/clips/job/clip_01.mp4"


def test_moviepy_fallback_with_captions_uses_caption_overlay(monkeypatch, tmp_path):
    _install_moviepy_fallback(monkeypatch, tmp_path)
    overlay_calls = []
    monkeypatch.setattr(
        video_editor,
        "_add_caption_overlays",
        lambda clip, captions, *_args: overlay_calls.append(captions) or clip,
    )

    result = video_editor.render_clip(
        "source.mp4",
        {"start": 0.0, "end": 5.0, "captions": [{"text": "caption", "start": 0.0, "end": 1.0}]},
        "job",
        0,
    )
    assert result["file"] == "/clips/job/clip_01.mp4"
    assert overlay_calls == [[{"text": "caption", "start": 0.0, "end": 1.0}]]
