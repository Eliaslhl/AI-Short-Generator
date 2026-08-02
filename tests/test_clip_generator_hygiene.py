"""ClipGenerator must never leave intermediate/unused files next to published clips."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

import backend.queue.worker as worker
from backend.config import settings
from backend.services.clip_generator import ClipGenerator, create_clip_generator
from backend.services.highlight_detector import HighlightSegment


def _make_source_video(path: Path, duration: int = 6) -> None:
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", f"color=c=red:s=320x240:r=10:d={duration}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def source_video(tmp_path_factory):
    path = tmp_path_factory.mktemp("clipgen-src") / "source.mp4"
    _make_source_video(path)
    return path


def test_only_the_final_mp4_is_published_no_orphans(tmp_path, source_video):
    gen = create_clip_generator(output_dir=str(tmp_path))

    result = gen.generate_from_highlight(
        video_path=str(source_video),
        highlight={"start_time": 1.0, "end_time": 4.0, "score": 90.0},
        apply_effects=True,
        output_formats=["mp4"],
        clip_id="clip_000",
    )

    assert result["mp4"] == str(tmp_path / "clip_000.mp4")
    # iterdir() lists dotfiles too, so a leaked ".clipgen-scratch-*" would show up here.
    published = sorted(p.name for p in tmp_path.iterdir())
    assert published == ["clip_000.mp4"], f"unexpected files left behind: {published}"


def test_effects_disabled_still_publishes_through_the_same_verified_path(tmp_path, source_video):
    gen = create_clip_generator(output_dir=str(tmp_path))

    result = gen.generate_from_highlight(
        video_path=str(source_video),
        highlight={"start_time": 0.5, "end_time": 3.0, "score": 50.0},
        apply_effects=False,
        output_formats=["mp4"],
        clip_id="clip_000",
    )

    assert result["mp4"] == str(tmp_path / "clip_000.mp4")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip_000.mp4"]


def test_two_close_timestamps_never_collide(tmp_path, source_video):
    gen = create_clip_generator(output_dir=str(tmp_path))

    first = gen.generate_from_highlight(
        video_path=str(source_video),
        highlight={"start_time": 1.4, "end_time": 3.4, "score": 80.0},
        output_formats=["mp4"],
        clip_id="clip_000",
    )
    second = gen.generate_from_highlight(
        video_path=str(source_video),
        highlight={"start_time": 1.6, "end_time": 3.6, "score": 70.0},
        output_formats=["mp4"],
        clip_id="clip_001",
    )

    assert first["mp4"] != second["mp4"]
    assert Path(first["mp4"]).is_file() and Path(second["mp4"]).is_file()
    assert Path(first["mp4"]).read_bytes() != Path(second["mp4"]).read_bytes()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip_000.mp4", "clip_001.mp4"]


def test_finalize_rejects_a_non_h264_candidate_without_publishing_anything(tmp_path, source_video):
    gen = create_clip_generator(output_dir=str(tmp_path))
    scratch = tempfile.mkdtemp(prefix="clipgen-test-")
    bad_candidate = os.path.join(scratch, "bad.mp4")
    # Encode with a codec that must fail the H.264/yuv420p contract check.
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(source_video),
            "-c:v", "mpeg4", "-pix_fmt", "yuv420p", "-an", bad_candidate,
        ],
        check=True,
        capture_output=True,
    )

    try:
        published = gen._finalize_clip(bad_candidate, scratch, "clip_bad")
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)

    assert published is None
    assert list(tmp_path.iterdir()) == []


def test_probe_final_mp4_accepts_video_only_clip_when_source_has_no_audio(tmp_path):
    silent = tmp_path / "silent-source.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=5:d=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", silent,
        ],
        check=True,
        capture_output=True,
    )
    gen = create_clip_generator(output_dir=str(tmp_path / "out"))

    result = gen.generate_from_highlight(
        video_path=str(silent),
        highlight={"start_time": 0.0, "end_time": 1.5, "score": 10.0},
        apply_effects=False,
        output_formats=["mp4"],
        clip_id="clip_silent",
    )

    assert result["mp4"] is not None
    assert Path(result["mp4"]).is_file()


def test_generate_clips_retry_leaves_no_accumulated_files(tmp_path, source_video, monkeypatch):
    """RQ may retry a job; a second _generate_clips run must not accumulate
    the previous attempt's clips or any intermediate file next to them."""
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))
    highlights = [HighlightSegment(1.0, 3.0, 90.0, 80.0, 70.0, 0.0, "event")]

    first_run = worker._generate_clips(highlights, str(source_video), "job-retry", max_clips=5)
    job_dir = tmp_path / "job-retry"
    assert sorted(p.name for p in job_dir.iterdir()) == ["clip_000.mp4"]
    first_bytes = (job_dir / first_run[0]["file"]).read_bytes()

    second_run = worker._generate_clips(highlights, str(source_video), "job-retry", max_clips=5)
    assert sorted(p.name for p in job_dir.iterdir()) == ["clip_000.mp4"]
    assert (job_dir / second_run[0]["file"]).read_bytes() == first_bytes


def test_generate_clips_sweeps_a_stranded_scratch_dir_from_a_killed_prior_attempt(
    tmp_path, source_video, monkeypatch
):
    """A hard kill mid-generation can strand a ".clipgen-scratch-*" directory
    before its own cleanup runs; the next attempt must sweep it, not leave it
    accumulating forever next to published clips."""
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))
    job_dir = tmp_path / "job-crashed"
    stranded = job_dir / ".clipgen-scratch-clip_000-deadbeef"
    stranded.mkdir(parents=True)
    (stranded / "clip_000.base.mp4").write_bytes(b"leftover-from-a-killed-worker")

    highlights = [HighlightSegment(1.0, 3.0, 90.0, 80.0, 70.0, 0.0, "event")]
    worker._generate_clips(highlights, str(source_video), "job-crashed", max_clips=5)

    assert not stranded.exists()
    assert sorted(p.name for p in job_dir.iterdir()) == ["clip_000.mp4"]
