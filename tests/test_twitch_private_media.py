"""Twitch/RQ clips must use the same private media boundary as normal jobs."""

import asyncio
import json
import logging
import math
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest
from sqlalchemy import func, select

import backend.api.advanced_routes as advanced_routes
import backend.queue.worker as worker
import backend.services.audio_processor as audio_processor
import backend.services.motion_processor as motion_processor
from backend.config import settings
from backend.main import app
from backend.models.user import Job, User
from backend.services.highlight_detector import HighlightDetector, HighlightSegment
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
        self.func = None
        self.args: tuple = ()
        self.kwargs: dict = {}

    def enqueue(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.job_id = kwargs["job_id"]
        self.meta = kwargs["meta"]
        return self.job_id

    def invoke_like_rq(self):
        """Invoke the captured target with exactly RQ's target arguments."""
        target_kwargs = {
            key: value
            for key, value in self.kwargs.items()
            if key not in {"job_id", "meta"}
        }
        return self.func(*self.args, **target_kwargs)


class _FailingQueue:
    def __init__(self):
        self.calls = 0

    def enqueue(self, *_args, **_kwargs):
        self.calls += 1
        raise OSError("Redis unavailable")


def _mutation_headers(session_factory, user_id: str, email: str) -> dict[str, str]:
    return {
        **_headers(session_factory, user_id, email),
        "Origin": "http://localhost:5173",
    }


def test_advanced_twitch_job_is_persisted_with_its_owner(http_client, monkeypatch):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    queue = _RecordingQueue()
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)

    async def create_job():
        async with session_factory() as session:
            owner = await session.get(User, data["owner_id"])
            response = await advanced_routes.generate_twitch_advanced(
                advanced_routes.TwitchAdvancedRequest(
                    url="https://www.twitch.tv/videos/123"
                ),
                owner,
                session,
            )
            job = await session.get(Job, response["job_id"])
            return response, job

    response, job = asyncio.run(create_job())

    assert job is not None
    assert job.user_id == data["owner_id"]
    assert job.youtube_url == "https://www.twitch.tv/videos/123"
    assert job.status == "pending"
    assert queue.job_id == response["job_id"]
    assert queue.meta == {"user_id": data["owner_id"]}
    assert queue.func is worker.process_twitch_video
    assert queue.args == (
        response["job_id"],
        data["owner_id"],
        "https://www.twitch.tv/videos/123",
    )
    assert queue.kwargs["max_clips"] == 5
    assert queue.kwargs["language"] == "en"
    assert "args" not in queue.kwargs
    assert "kwargs" not in queue.kwargs


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

    status = client.get(f"/api/status/twitch/{data['job_id']}", headers=headers)
    media = client.get(status.json()["clips"][0]["file"], headers=headers)

    assert clips[0]["file"] == "twitch-clip.mp4"
    assert (tmp_path / data["job_id"] / "twitch-clip.mp4").is_file()
    assert status.status_code == 200
    assert status.json()["clips"][0]["file"] == (
        f"/api/jobs/{data['job_id']}/clips/0/media"
    )
    assert media.status_code == 200
    assert media.content == b"twitch-private-media"


def test_advanced_route_enqueues_and_executes_the_real_worker_with_local_video(
    http_client, tmp_path, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    queue = _RecordingQueue()
    monkeypatch.setattr(settings, "video_temp_dir", str(tmp_path / "worker-tmp"))
    workspace = worker._create_twitch_download_workspace()
    source = workspace / "source.mp4"
    source.write_bytes(b"synthetic-video")
    clips_root = tmp_path / "clips"
    seen_segment_paths: list[str] = []

    monkeypatch.setattr(settings, "clips_dir", str(clips_root))
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: worker.TwitchDownloadedSource(
            path=str(source), workspace=workspace
        )
    )

    def segment(local_path, _chunk_duration):
        seen_segment_paths.append(local_path)
        return [{"chunk_id": "000", "path": local_path, "duration": 10.0}]

    def generate(_highlights, _video_path, job_id, _max_clips):
        output_dir = clips_root / job_id
        output_dir.mkdir(parents=True)
        (output_dir / "clip_000.mp4").write_bytes(b"first-private-clip")
        (output_dir / "clip_001.mp4").write_bytes(b"second-private-clip")
        return [
            {"clip_id": "clip_000", "file": "clip_000.mp4"},
            {"clip_id": "clip_001", "file": "clip_001.mp4"},
        ]

    monkeypatch.setattr(worker, "_segment_video", segment)
    monkeypatch.setattr(
        worker,
        "_process_chunk",
        lambda *_args: [SimpleNamespace(start_time=0.0, end_time=3.0, score=9.0)],
    )
    monkeypatch.setattr(worker, "_generate_clips", generate)

    response = client.post(
        "/api/generate/twitch/advanced",
        json={"url": "https://www.twitch.tv/videos/123", "max_clips": 2},
        headers=_mutation_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert queue.args == (job_id, data["owner_id"], "https://www.twitch.tv/videos/123")
    assert queue.kwargs["max_clips"] == 2
    assert queue.kwargs["language"] == "en"
    assert "args" not in queue.kwargs
    assert "kwargs" not in queue.kwargs

    result = queue.invoke_like_rq()
    assert result["success"] is True
    assert seen_segment_paths == [str(source)]
    assert not workspace.exists()

    async def read_result():
        async with session_factory() as session:
            job = await session.get(Job, job_id)
            owner = await session.get(User, data["owner_id"])
            return job, owner

    job, owner = asyncio.run(read_result())
    assert job.status == "done"
    assert job.progress == 100
    assert job.error is None
    assert json.loads(job.clips_json) == [
        {"clip_id": "clip_000", "file": "clip_000.mp4"},
        {"clip_id": "clip_001", "file": "clip_001.mp4"},
    ]
    assert owner.twitch_generations_month == 1

    media = client.get(
        f"/api/jobs/{job_id}/clips/0/media",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )
    assert media.status_code == 200
    assert media.content == b"first-private-clip"


def test_advanced_route_refuses_exhausted_twitch_quota_before_job_or_enqueue(
    http_client, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    queue = _RecordingQueue()
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)

    async def exhaust_quota():
        async with session_factory() as session:
            owner = await session.get(User, data["owner_id"])
            owner.twitch_generations_month = owner.twitch_limit
            await session.commit()

    asyncio.run(exhaust_quota())
    response = client.post(
        "/api/generate/twitch/advanced",
        json={"url": "https://www.twitch.tv/videos/123"},
        headers=_mutation_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 402
    assert response.json()["detail"]["error"] == "quota_exceeded"
    assert queue.job_id is None

    async def counts():
        async with session_factory() as session:
            job_count = await session.scalar(select(func.count()).select_from(Job))
            owner = await session.get(User, data["owner_id"])
            return job_count, owner.twitch_generations_month, owner.twitch_limit

    job_count, usage, limit = asyncio.run(counts())
    assert job_count == 1
    assert usage == limit


def test_advanced_route_rejects_lookalike_twitch_domain_before_quota_or_enqueue(
    http_client, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    queue = _RecordingQueue()
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)

    response = client.post(
        "/api/generate/twitch/advanced",
        json={"url": "https://twitch.tv.attacker.test/videos/123"},
        headers=_mutation_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Twitch URL"}
    assert queue.job_id is None

    async def unchanged_state():
        async with session_factory() as session:
            jobs = await session.scalar(select(func.count()).select_from(Job))
            owner = await session.get(User, data["owner_id"])
            return jobs, owner.twitch_generations_month

    assert asyncio.run(unchanged_state()) == (1, 0)


def test_advanced_route_rolls_back_job_and_quota_when_enqueue_fails(
    http_client, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    queue = _FailingQueue()
    monkeypatch.setattr(advanced_routes, "get_queue", lambda: queue)

    response = client.post(
        "/api/generate/twitch/advanced",
        json={"url": "https://www.twitch.tv/videos/123"},
        headers=_mutation_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to start processing"}
    assert queue.calls == 1

    async def rollback_state():
        async with session_factory() as session:
            jobs = await session.scalar(select(func.count()).select_from(Job))
            owner = await session.get(User, data["owner_id"])
            return jobs, owner.twitch_generations_month

    assert asyncio.run(rollback_state()) == (1, 0)


def test_invalid_download_duration_persists_a_failed_job_and_refunds_twitch_quota(
    http_client, tmp_path, monkeypatch
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    source = tmp_path / "downloaded.mp4"
    source.write_bytes(b"synthetic-video")
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(worker, "_download_twitch_video", lambda *_args: str(source))
    monkeypatch.setattr(worker, "_segment_video", lambda *_args: [])

    async def charge_quota():
        async with session_factory() as session:
            owner = await session.get(User, data["owner_id"])
            job = await session.get(Job, data["job_id"])
            owner.twitch_generations_month = 1
            job.status = "pending"
            job.progress = 0
            await session.commit()

    asyncio.run(charge_quota())
    with pytest.raises(RuntimeError, match="Twitch processing failed"):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )

    async def read_failure():
        async with session_factory() as session:
            job = await session.get(Job, data["job_id"])
            owner = await session.get(User, data["owner_id"])
            return job.status, job.error, json.loads(job.clips_json), owner.twitch_generations_month

    assert asyncio.run(read_failure()) == ("error", "Processing failed", [], 0)


def test_repeated_failed_worker_invocation_does_not_refund_twitch_quota_twice(
    http_client, tmp_path, monkeypatch
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    source = tmp_path / "downloaded.mp4"
    source.write_bytes(b"synthetic-video")
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(worker, "_download_twitch_video", lambda *_args: str(source))
    monkeypatch.setattr(worker, "_segment_video", lambda *_args: [])

    async def charge_quota():
        async with session_factory() as session:
            owner = await session.get(User, data["owner_id"])
            job = await session.get(Job, data["job_id"])
            owner.twitch_generations_month = 1
            job.status = "pending"
            job.progress = 0
            await session.commit()

    asyncio.run(charge_quota())
    with pytest.raises(RuntimeError, match="Twitch processing failed"):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )
    repeated = worker.process_twitch_video(
        data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
    )

    async def final_state():
        async with session_factory() as session:
            job = await session.get(Job, data["job_id"])
            owner = await session.get(User, data["owner_id"])
            return job.status, owner.twitch_generations_month

    assert repeated == {"success": False, "job_id": data["job_id"], "error": "Job is not available for processing"}
    assert asyncio.run(final_state()) == ("error", 0)


@pytest.mark.parametrize(
    "url",
    (
        "https://evil.example@twitch.tv/videos/123",
        "https://www.twitch.tv:444/videos/123",
        "https://www.twitch.tv/videos/123?token=sensitive",
        "https://www.twitch.tv/videos/123#fragment",
        "https://twitch.tv.evil.example/videos/123",
        "https://www.twitch.tv//videos/123",
    ),
)
def test_twitch_vod_url_validation_rejects_noncanonical_or_sensitive_urls(url):
    assert advanced_routes._is_twitch_vod_url(url) is False


def test_openapi_exposes_advanced_routes_once_under_api_prefix():
    paths = app.openapi()["paths"]
    assert "/api/generate/twitch/advanced" in paths
    assert "/api/status/twitch/{job_id}" in paths
    assert "/api/jobs/{job_id}" in paths
    assert not any(path.startswith("/api/api/") for path in paths)


def test_generated_clip_validation_rejects_missing_empty_and_unsafe_references(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))
    job_dir = tmp_path / "job-123"
    job_dir.mkdir()
    (job_dir / "valid.mp4").write_bytes(b"clip")
    (job_dir / "empty.mp4").write_bytes(b"")

    clips = worker._validate_generated_clips(
        [
            {"file": "valid.mp4"},
            {"file": "empty.mp4"},
            {"file": "missing.mp4"},
            {"file": "../outside.mp4"},
            {"file": "/tmp/outside.mp4"},
            {"file": "folder\\outside.mp4"},
        ],
        "job-123",
    )

    assert clips == [{"file": "valid.mp4"}]


def _owned_twitch_source(tmp_path, monkeypatch, content=b"synthetic-video"):
    monkeypatch.setattr(settings, "video_temp_dir", str(tmp_path / "worker-tmp"))
    workspace = worker._create_twitch_download_workspace()
    source = workspace / "source.mp4"
    source.write_bytes(content)
    return workspace, source


def _owned_twitch_download(workspace, source):
    return worker.TwitchDownloadedSource(path=str(source), workspace=workspace)


def _create_two_event_video(path: Path) -> None:
    """Create two deterministic visual events without retaining test fixtures."""
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=64x64:r=8:d=10",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=64x64:r=8:d=10",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def test_process_chunk_uses_module_processors_with_a_bounded_window_and_offset(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"synthetic-video")
    calls = []
    local_highlight = HighlightSegment(1.0, 4.0, 90.0, 80.0, 70.0, 0.0, "event")

    def audio_processor(path, **kwargs):
        calls.append(("audio", path, kwargs))
        return {"audio": np.array([0.1, 0.2])}

    def motion_processor(path, **kwargs):
        calls.append(("motion", path, kwargs))
        return {"frame_differences": np.array([0.0, 1.0]), "analysis_fps": 15.0}

    class Detector:
        def __init__(self, **_kwargs):
            pass

        def detect_highlights(self, **kwargs):
            assert kwargs["audio_data"].tolist() == [0.1, 0.2]
            assert kwargs["frame_diffs"] == [0.0, 1.0]
            assert kwargs["segment_duration"] == 10.0
            assert kwargs["motion_fps"] == 15.0
            return [local_highlight]

    monkeypatch.setattr(worker, "process_audio_for_highlight_detection", audio_processor)
    monkeypatch.setattr(worker, "process_video_for_motion_detection", motion_processor)
    monkeypatch.setattr(worker, "HighlightDetector", Detector)

    highlights = worker._process_chunk(
        {
            "chunk_id": "001",
            "path": str(source),
            "start_time": 10.0,
            "duration": 10.0,
            "source_duration": 20.0,
        },
        "en",
    )

    assert calls == [
        ("audio", str(source), {"sample_rate": 22050, "start_time": 10.0, "duration": 10.0}),
        ("motion", str(source), {"fps": 30, "start_time": 10.0, "duration": 10.0}),
    ]
    assert [(item.start_time, item.end_time) for item in highlights] == [(11.0, 14.0)]
    assert (local_highlight.start_time, local_highlight.end_time) == (1.0, 4.0)


@pytest.mark.parametrize(
    "chunk",
    [
        {"start_time": float("nan"), "duration": 10.0},
        {"start_time": 0.0, "duration": float("inf")},
        {"start_time": 0.0, "duration": 0.0},
        {"start_time": 15.0, "duration": 10.0, "source_duration": 20.0},
    ],
)
def test_process_chunk_rejects_invalid_timing_before_running_processors(
    tmp_path, monkeypatch, chunk
):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"synthetic-video")
    chunk.update({"chunk_id": "invalid", "path": str(source)})
    monkeypatch.setattr(
        worker,
        "process_audio_for_highlight_detection",
        lambda *_args, **_kwargs: pytest.fail("audio processor must not run"),
    )

    with pytest.raises(ValueError):
        worker._process_chunk(chunk, "en")


def test_process_chunk_surfaces_processor_failures(tmp_path, monkeypatch, caplog):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"synthetic-video")
    monkeypatch.setattr(
        worker,
        "process_audio_for_highlight_detection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("decoder failed")),
    )

    with caplog.at_level(logging.ERROR), pytest.raises(
        RuntimeError, match="Twitch chunk analysis failed"
    ):
        worker._process_chunk(
            {"chunk_id": "001", "path": str(source), "start_time": 0.0, "duration": 10.0},
            "en",
        )

    assert str(source) not in caplog.text
    assert "exception_type=OSError" in caplog.text


def test_process_chunk_rejects_a_missing_source_before_running_processors(monkeypatch):
    monkeypatch.setattr(
        worker,
        "process_audio_for_highlight_detection",
        lambda *_args, **_kwargs: pytest.fail("audio processor must not run"),
    )

    with pytest.raises(ValueError, match="source is unavailable"):
        worker._process_chunk(
            {"chunk_id": "missing", "path": "missing.mp4", "start_time": 0.0, "duration": 10.0},
            "en",
        )


def test_offset_highlight_rejects_invalid_local_timestamps_without_mutating_input():
    highlight = HighlightSegment(float("nan"), 4.0, 90.0, 80.0, 70.0, 0.0, "event")

    with pytest.raises(ValueError, match="must be finite"):
        worker._offset_highlight(highlight, 10.0, 10.0, 20.0)

    assert math.isnan(highlight.start_time)


def test_process_chunk_allows_motion_only_analysis_when_source_has_no_audio(
    tmp_path, monkeypatch
):
    source = tmp_path / "silent.mp4"
    source.write_bytes(b"synthetic-video")
    monkeypatch.setattr(
        worker,
        "process_audio_for_highlight_detection",
        lambda *_args, **_kwargs: {"audio": np.array([])},
    )
    monkeypatch.setattr(
        worker,
        "process_video_for_motion_detection",
        lambda *_args, **_kwargs: {"frame_differences": np.array([0.0, 1.0])},
    )

    class Detector:
        def __init__(self, **_kwargs):
            pass

        def detect_highlights(self, **kwargs):
            assert kwargs["audio_data"].size == 0
            assert kwargs["frame_diffs"] == [0.0, 1.0]
            return []

    monkeypatch.setattr(worker, "HighlightDetector", Detector)

    assert worker._process_chunk(
        {"chunk_id": "000", "path": str(source), "start_time": 0.0, "duration": 10.0},
        "en",
    ) == []


def test_audio_processor_loads_only_the_requested_window(monkeypatch):
    calls = []

    class Librosa:
        def load(self, *args, **kwargs):
            calls.append((args, kwargs))
            return np.array([0.1]), 22050

    monkeypatch.setattr(audio_processor, "_get_librosa", lambda: Librosa())

    audio_processor.RealAudioProcessor().load_audio_from_file(
        "source.mp4", start_time=10.0, duration=5.0
    )

    assert calls == [
        (("source.mp4",), {"sr": 22050, "mono": True, "offset": 10.0, "duration": 5.0})
    ]


def test_audio_processor_treats_a_confirmed_missing_audio_stream_as_motion_only(
    tmp_path,
):
    source = tmp_path / "silent.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=16x16:r=4:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
        capture_output=True,
    )

    result = audio_processor.process_audio_for_highlight_detection(
        str(source), start_time=0.0, duration=1.0
    )

    assert result["audio"].size == 0
    assert result["rms_energy"].size == 0


def test_audio_processor_does_not_mask_a_decoder_failure_as_missing_audio(monkeypatch):
    class NoBackendError(Exception):
        pass

    class Librosa:
        def load(self, *_args, **_kwargs):
            raise NoBackendError("decoder failed")

    monkeypatch.setattr(audio_processor, "_get_librosa", lambda: Librosa())
    monkeypatch.setattr(audio_processor, "_source_has_audio_stream", lambda _path: True)

    with pytest.raises(NoBackendError):
        audio_processor.RealAudioProcessor().load_audio_from_file("source.mp4")


def test_motion_processor_forwards_the_requested_window(monkeypatch):
    calls = []

    class Processor:
        def __init__(self, fps):
            assert fps == 30

        def load_video_frames(self, path, **kwargs):
            calls.append((path, kwargs))
            return [np.zeros((2, 2), dtype=np.uint8)], 30, (2, 2)

        def compute_frame_differences(self, _frames):
            return np.array([0.0])

        def detect_scene_changes(self, _frames):
            return np.array([0.0])

    monkeypatch.setattr(motion_processor, "MotionProcessor", Processor)

    motion_processor.process_video_for_motion_detection(
        "source.mp4", start_time=10.0, duration=5.0
    )

    assert calls == [
        (
            "source.mp4",
            {"max_frames": None, "skip_frames": 2, "start_time": 10.0, "duration": 5.0},
        )
    ]


def test_motion_processor_discards_frames_before_seek_and_at_chunk_end(monkeypatch):
    frames = [
        (9.5, np.zeros((2, 2, 3), dtype=np.uint8)),
        (10.0, np.ones((2, 2, 3), dtype=np.uint8)),
        (19.5, np.full((2, 2, 3), 2, dtype=np.uint8)),
        (20.0, np.full((2, 2, 3), 3, dtype=np.uint8)),
    ]

    class Capture:
        def __init__(self):
            self.position = 0.0
            self.set_calls = []

        def isOpened(self):
            return True

        def get(self, property_id):
            if property_id == motion_processor.cv2.CAP_PROP_FPS:
                return 10
            if property_id == motion_processor.cv2.CAP_PROP_FRAME_COUNT:
                return 1000
            if property_id == motion_processor.cv2.CAP_PROP_FRAME_HEIGHT:
                return 2
            if property_id == motion_processor.cv2.CAP_PROP_FRAME_WIDTH:
                return 2
            if property_id == motion_processor.cv2.CAP_PROP_POS_MSEC:
                return self.position * 1000
            raise AssertionError(property_id)

        def set(self, property_id, value):
            self.set_calls.append((property_id, value))

        def read(self):
            if not frames:
                return False, None
            self.position, frame = frames.pop(0)
            return True, frame

        def release(self):
            pass

    capture = Capture()
    monkeypatch.setattr(motion_processor.cv2, "VideoCapture", lambda _path: capture)

    loaded, fps, _dimensions = motion_processor.MotionProcessor().load_video_frames(
        "source.mp4", start_time=10.0, duration=10.0
    )

    assert capture.set_calls == [(motion_processor.cv2.CAP_PROP_POS_MSEC, 10000.0)]
    assert fps == 10
    assert len(loaded) == 2


def test_highlight_detector_uses_the_motion_sampling_rate_for_window_positions(monkeypatch):
    detector = HighlightDetector()
    indices = []

    def score(_frame_diffs, window_idx, **_kwargs):
        indices.append(window_idx)
        return 0.0

    monkeypatch.setattr(detector.motion_analyzer, "compute_motion_score", score)

    detector.detect_highlights(
        frame_diffs=[0.0] * 500,
        segment_duration=30.0,
        window_size=15.0,
        overlap=0.5,
        motion_fps=15.0,
    )

    assert indices == [0, 112, 225]


def test_twitch_chunk_pipeline_offsets_two_chunks_before_generating_distinct_clips(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.mp4"
    _create_two_event_video(source)
    clips_root = tmp_path / "clips"
    monkeypatch.setattr(settings, "clips_dir", str(clips_root))
    monkeypatch.setattr(
        worker,
        "create_download_manager",
        lambda: SimpleNamespace(get_video_duration=lambda _path: 20.0),
    )
    monkeypatch.setattr(
        worker,
        "process_audio_for_highlight_detection",
        lambda *_args, **_kwargs: {"audio": np.array([0.5, 0.5])},
    )
    monkeypatch.setattr(
        worker,
        "process_video_for_motion_detection",
        lambda *_args, **_kwargs: {"frame_differences": np.array([0.0, 1.0])},
    )

    class Detector:
        def __init__(self, **_kwargs):
            pass

        def detect_highlights(self, **_kwargs):
            return [HighlightSegment(1.0, 4.0, 90.0, 80.0, 70.0, 0.0, "event")]

    monkeypatch.setattr(worker, "HighlightDetector", Detector)

    chunks = worker._segment_video(str(source), chunk_duration=10)
    highlights = [highlight for chunk in chunks for highlight in worker._process_chunk(chunk, "en")]
    clips = worker._generate_clips(highlights, str(source), "job-123", max_clips=2)

    assert [(item.start_time, item.end_time) for item in highlights] == [(1.0, 4.0), (11.0, 14.0)]
    assert len(clips) == 2
    assert [item["duration"] for item in clips] == [3.0, 3.0]
    clip_paths = [clips_root / "job-123" / item["file"] for item in clips]
    assert all(path.is_file() and path.suffix == ".mp4" for path in clip_paths)
    assert clip_paths[0].read_bytes() != clip_paths[1].read_bytes()
    assert not list(tmp_path.glob("chunk*.mp4"))


def _make_twitch_job_pending(session_factory, job_id):
    async def update_job():
        async with session_factory() as session:
            job = await session.get(Job, job_id)
            job.status = "pending"
            job.progress = 0
            job.error = None
            job.clips_json = json.dumps([])
            await session.commit()

    asyncio.run(update_job())


def test_twitch_worker_cleans_owned_source_after_success_and_keeps_final_clips(
    http_client, tmp_path, monkeypatch
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    _make_twitch_job_pending(session_factory, data["job_id"])
    clips_root = tmp_path / "clips"
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "clips_dir", str(clips_root))
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: _owned_twitch_download(workspace, source)
    )
    monkeypatch.setattr(
        worker,
        "_segment_video",
        lambda path, _duration: [{"chunk_id": "000", "path": path, "duration": 1.0}],
    )
    monkeypatch.setattr(
        worker,
        "_process_chunk",
        lambda *_args: [SimpleNamespace(start_time=0.0, end_time=1.0, score=1.0)],
    )

    def generate(_highlights, _source, job_id, _max_clips):
        clip = clips_root / job_id / "clip_000.mp4"
        clip.parent.mkdir(parents=True, exist_ok=True)
        clip.write_bytes(b"final-clip")
        return [{"clip_id": "clip_000", "file": "clip_000.mp4"}]

    monkeypatch.setattr(worker, "_generate_clips", generate)

    result = worker.process_twitch_video(
        data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
    )

    assert result["success"] is True
    assert not workspace.exists()
    assert (clips_root / data["job_id"] / "clip_000.mp4").read_bytes() == b"final-clip"


@pytest.mark.parametrize("segment", [lambda *_args: [], lambda *_args: (_ for _ in ()).throw(OSError("boom"))])
def test_twitch_worker_cleans_owned_source_after_segmentation_failure(
    http_client, tmp_path, monkeypatch, segment
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    _make_twitch_job_pending(session_factory, data["job_id"])
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: _owned_twitch_download(workspace, source)
    )
    monkeypatch.setattr(worker, "_segment_video", segment)

    with pytest.raises(RuntimeError, match="Twitch processing failed"):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )

    assert not workspace.exists()


def test_twitch_worker_cleans_empty_owned_source_after_validation_failure(
    http_client, tmp_path, monkeypatch
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    _make_twitch_job_pending(session_factory, data["job_id"])
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch, content=b"")
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: _owned_twitch_download(workspace, source)
    )

    with pytest.raises(RuntimeError, match="Twitch processing failed"):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )

    assert not workspace.exists()


def test_twitch_worker_cleans_owned_source_when_no_clips_are_generated(
    http_client, tmp_path, monkeypatch
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    _make_twitch_job_pending(session_factory, data["job_id"])
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: _owned_twitch_download(workspace, source)
    )
    monkeypatch.setattr(
        worker,
        "_segment_video",
        lambda path, _duration: [{"chunk_id": "000", "path": path, "duration": 1.0}],
    )
    monkeypatch.setattr(worker, "_process_chunk", lambda *_args: [])
    monkeypatch.setattr(worker, "_generate_clips", lambda *_args: [])

    with pytest.raises(RuntimeError, match="Twitch processing failed"):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )

    assert not workspace.exists()


def test_twitch_download_cleanup_removes_partial_files_after_downloader_failure(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "video_temp_dir", str(tmp_path / "worker-tmp"))
    monkeypatch.setattr(
        worker,
        "create_twitch_client",
        lambda: SimpleNamespace(parse_twitch_url=lambda _url: {"type": "vod", "id": "123"}),
    )

    class PartialDownloader:
        def download_twitch_vod(self, **kwargs):
            output = Path(kwargs["output_path"])
            output.with_suffix(".part").write_bytes(b"partial")
            raise OSError("network failure")

    monkeypatch.setattr(worker, "create_download_manager", lambda: PartialDownloader())

    assert worker._download_twitch_video("https://www.twitch.tv/videos/123", "job") is None
    assert not any(worker._twitch_download_temp_root().iterdir())


def test_twitch_downloader_cannot_return_a_source_from_another_workspace(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "video_temp_dir", str(tmp_path / "worker-tmp"))
    other_workspace = worker._create_twitch_download_workspace()
    other_source = other_workspace / "source.mp4"
    other_source.write_bytes(b"other-job-source")
    monkeypatch.setattr(
        worker,
        "create_twitch_client",
        lambda: SimpleNamespace(parse_twitch_url=lambda _url: {"type": "vod", "id": "123"}),
    )
    monkeypatch.setattr(
        worker,
        "create_download_manager",
        lambda: SimpleNamespace(download_twitch_vod=lambda **_kwargs: str(other_source)),
    )

    assert worker._download_twitch_video("https://www.twitch.tv/videos/123", "job") is None
    assert other_source.read_bytes() == b"other-job-source"
    worker._cleanup_twitch_download_workspace(other_workspace, "other-job")


def test_twitch_cleanup_refuses_external_paths_and_only_unlinks_symlinks(tmp_path, monkeypatch):
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    external = tmp_path / "outside.mp4"
    external.write_bytes(b"outside")
    source.unlink()
    source.symlink_to(external)

    worker._cleanup_twitch_download_workspace(workspace, "job")

    assert external.read_bytes() == b"outside"
    assert not source.exists()
    assert not workspace.exists()

    worker._cleanup_twitch_download_workspace(tmp_path, "job")
    assert external.read_bytes() == b"outside"
    worker._cleanup_twitch_download_workspace(tmp_path / "missing", "job")


def test_twitch_cleanup_refuses_directories_and_logs_without_local_path(
    tmp_path, monkeypatch, caplog
):
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    nested = workspace / "unexpected-directory"
    nested.mkdir()

    with caplog.at_level(logging.WARNING):
        worker._cleanup_twitch_download_workspace(workspace, "job-123")

    assert not source.exists()
    assert nested.is_dir()
    assert workspace.is_dir()
    assert str(workspace) not in caplog.text
    assert "exception_type=OSError" in caplog.text


def test_twitch_cleanup_does_not_follow_a_workspace_replaced_by_a_symlink(
    tmp_path, monkeypatch
):
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    external_directory = tmp_path / "external"
    external_directory.mkdir()
    external_file = external_directory / "keep.mp4"
    external_file.write_bytes(b"external")
    moved_workspace = workspace.with_name(f"{workspace.name}-moved")
    original_listdir = os.listdir
    swapped = False

    def swap_workspace_after_open(file_descriptor):
        nonlocal swapped
        if not swapped:
            swapped = True
            workspace.rename(moved_workspace)
            workspace.symlink_to(external_directory, target_is_directory=True)
        return original_listdir(file_descriptor)

    monkeypatch.setattr(worker.os, "listdir", swap_workspace_after_open)

    worker._cleanup_twitch_download_workspace(workspace, "job")

    assert external_file.read_bytes() == b"external"
    assert not (moved_workspace / source.name).exists()
    assert workspace.is_symlink()


def test_twitch_worker_cleans_source_when_success_persistence_fails(
    http_client, tmp_path, monkeypatch
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    _make_twitch_job_pending(session_factory, data["job_id"])
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    clips_root = tmp_path / "clips"
    clip = clips_root / data["job_id"] / "clip_000.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"final-clip")
    monkeypatch.setattr(settings, "clips_dir", str(clips_root))
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: _owned_twitch_download(workspace, source)
    )
    monkeypatch.setattr(
        worker,
        "_segment_video",
        lambda path, _duration: [{"chunk_id": "000", "path": path, "duration": 1.0}],
    )
    monkeypatch.setattr(
        worker,
        "_process_chunk",
        lambda *_args: [SimpleNamespace(start_time=0.0, end_time=1.0, score=1.0)],
    )
    monkeypatch.setattr(worker, "_generate_clips", lambda *_args: [{"file": "clip_000.mp4"}])

    async def persist(_job_id, _clips, status, *_args, **_kwargs):
        if status == "done":
            raise OSError("database unavailable")

    monkeypatch.setattr(worker, "_persist_twitch_job_result", persist)

    with pytest.raises(RuntimeError, match="Twitch processing failed"):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )

    assert not workspace.exists()


@pytest.mark.parametrize("failed_processor", ["audio", "motion"])
def test_twitch_worker_refunds_and_cleans_up_after_processor_failure(
    http_client, tmp_path, monkeypatch, failed_processor
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    _make_twitch_job_pending(session_factory, data["job_id"])
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: _owned_twitch_download(workspace, source)
    )
    monkeypatch.setattr(
        worker,
        "_segment_video",
        lambda path, _duration: [{"chunk_id": "000", "path": path, "start_time": 0.0, "duration": 1.0}],
    )

    def fail(*_args, **_kwargs):
        raise OSError("processor unavailable")

    if failed_processor == "audio":
        monkeypatch.setattr(worker, "process_audio_for_highlight_detection", fail)
    else:
        monkeypatch.setattr(
            worker,
            "process_audio_for_highlight_detection",
            lambda *_args, **_kwargs: {"audio": np.array([])},
        )
        monkeypatch.setattr(worker, "process_video_for_motion_detection", fail)

    async def charge_quota():
        async with session_factory() as session:
            owner = await session.get(User, data["owner_id"])
            owner.twitch_generations_month = 1
            await session.commit()

    asyncio.run(charge_quota())
    with pytest.raises(RuntimeError, match="Twitch processing failed"):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )

    async def failure_state():
        async with session_factory() as session:
            job = await session.get(Job, data["job_id"])
            owner = await session.get(User, data["owner_id"])
            return job.status, job.error, json.loads(job.clips_json), owner.twitch_generations_month

    assert asyncio.run(failure_state()) == ("error", "Processing failed", [], 0)
    assert not workspace.exists()


def test_twitch_worker_cleanup_does_not_mask_refund_persistence_failure(
    http_client, tmp_path, monkeypatch
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    _make_twitch_job_pending(session_factory, data["job_id"])
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: _owned_twitch_download(workspace, source)
    )
    monkeypatch.setattr(worker, "_segment_video", lambda *_args: [])

    async def persist(*_args, **_kwargs):
        raise OSError("database unavailable")

    monkeypatch.setattr(worker, "_persist_twitch_job_result", persist)

    with pytest.raises(RuntimeError, match="Twitch processing failed"):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )

    assert not workspace.exists()


def test_twitch_worker_cleanup_failure_is_best_effort_and_does_not_mask_error(
    http_client, tmp_path, monkeypatch, caplog
):
    _, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    _make_twitch_job_pending(session_factory, data["job_id"])
    workspace, source = _owned_twitch_source(tmp_path, monkeypatch)
    monkeypatch.setattr(worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        worker, "_download_twitch_video", lambda *_args: _owned_twitch_download(workspace, source)
    )
    monkeypatch.setattr(worker, "_segment_video", lambda *_args: [])
    original_unlink = os.unlink

    def fail_source_unlink(path, *args, **kwargs):
        if path == source.name:
            raise PermissionError("denied")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(worker.os, "unlink", fail_source_unlink)

    with caplog.at_level(logging.WARNING), pytest.raises(
        RuntimeError, match="Twitch processing failed"
    ):
        worker.process_twitch_video(
            data["job_id"], data["owner_id"], "https://www.twitch.tv/videos/123"
        )

    assert source.is_file()
    assert "temporary source cleanup failed" in caplog.text
    assert str(source) not in caplog.text
    assert str(workspace) not in caplog.text


def test_twitch_download_workspaces_are_unique_per_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "video_temp_dir", str(tmp_path / "worker-tmp"))
    first = worker._create_twitch_download_workspace()
    second = worker._create_twitch_download_workspace()

    assert first != second
    worker._cleanup_twitch_download_workspace(first, "job")
    worker._cleanup_twitch_download_workspace(second, "job")
    assert not first.exists()
    assert not second.exists()
