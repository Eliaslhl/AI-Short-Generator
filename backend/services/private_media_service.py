"""Safe private clip resolution and byte-range streaming."""
import json
import mimetypes
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

CHUNK_SIZE = 64 * 1024

_PUBLIC_METADATA_KEYS = frozenset(
    {
        "captions",
        "clip_id",
        "duration",
        "end",
        "end_time",
        "hashtags",
        "hook",
        "keywords",
        "score",
        "start",
        "start_time",
        "text",
        "title",
        "viral_score",
    }
)


class MediaNotFound(Exception):
    pass


class InvalidRange(Exception):
    pass


@dataclass
class OpenedClip:
    """An opened private clip whose descriptor owns the media snapshot."""

    fd: int | None
    name: str
    size: int


def public_clip_payloads(job_id: str, clips_json: str | list[Any] | None) -> list[dict]:
    """Return clip metadata with storage references replaced by private URLs."""
    if isinstance(clips_json, str):
        try:
            clips = json.loads(clips_json)
        except (TypeError, ValueError):
            return []
    else:
        clips = clips_json

    if not isinstance(clips, list):
        return []

    payloads = []
    for index, clip in enumerate(clips):
        metadata = (
            {key: clip[key] for key in _PUBLIC_METADATA_KEYS if key in clip}
            if isinstance(clip, dict)
            else {}
        )
        media_url = f"/api/jobs/{job_id}/clips/{index}/media"
        payloads.append(
            {
                **metadata,
                "index": index,
                "file": media_url,
                "download_url": f"{media_url}?download=true",
            }
        )
    return payloads


def clip_at(clips_json: str | None, index: int) -> dict:
    if index < 0:
        raise MediaNotFound
    try:
        clips = json.loads(clips_json or "[]")
    except (TypeError, ValueError):
        raise MediaNotFound from None
    if not isinstance(clips, list) or index >= len(clips) or not isinstance(clips[index], dict):
        raise MediaNotFound
    return clips[index]


def validated_clip_filename(reference: object, job_id: str) -> str:
    """Validate a complete stored reference before extracting its filename."""
    if not isinstance(reference, str) or not reference or any(
        character in reference for character in ("\r", "\n", "\x00", "?", "#", "%")
    ):
        raise MediaNotFound

    if reference.startswith("/clips/"):
        parts = reference.split("/")
        if len(parts) != 4 or parts[2] != job_id:
            raise MediaNotFound
        filename_value = parts[3]
    else:
        filename_value = reference

    if (
        filename_value in {"", ".", ".."}
        or "/" in filename_value
        or "\\" in filename_value
        or ":" in filename_value
        or filename_value.startswith(".")
    ):
        raise MediaNotFound
    return filename_value


def _close_fd(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass


def close_clip(clip: OpenedClip) -> None:
    if clip.fd is None:
        return
    fd, clip.fd = clip.fd, None
    _close_fd(fd)


def _require_safe_open_support() -> None:
    if not getattr(os, "O_NOFOLLOW", 0) or os.open not in os.supports_dir_fd:
        raise MediaNotFound


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | os.O_NOFOLLOW
    )


def _regular_file_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | os.O_NOFOLLOW
    )


def _require_directory(fd: int) -> None:
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        raise MediaNotFound


def _validate_job_id(job_id: object) -> str:
    if (
        not isinstance(job_id, str)
        or not job_id
        or job_id in {".", ".."}
        or any(character in job_id for character in ("/", "\\", "\r", "\n", "\x00"))
    ):
        raise MediaNotFound
    return job_id


def open_clip(clips_root: str, job_id: str, clip: dict) -> OpenedClip:
    """Atomically open a clip relative to its job directory without following links."""
    safe_job_id = _validate_job_id(job_id)
    reference = clip.get("file") or clip.get("path")
    filename_value = validated_clip_filename(reference, safe_job_id)

    _require_safe_open_support()
    root_fd = job_fd = file_fd = -1
    ownership_transferred = False
    try:
        root_fd = os.open(str(Path(clips_root).resolve()), _directory_flags())
        _require_directory(root_fd)
        job_fd = os.open(safe_job_id, _directory_flags(), dir_fd=root_fd)
        _require_directory(job_fd)
        file_fd = os.open(filename_value, _regular_file_flags(), dir_fd=job_fd)
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise MediaNotFound
        opened_clip = OpenedClip(fd=file_fd, name=filename_value, size=metadata.st_size)
        ownership_transferred = True
        return opened_clip
    except (OSError, ValueError):
        raise MediaNotFound from None
    finally:
        if file_fd != -1 and not ownership_transferred:
            _close_fd(file_fd)
        if job_fd != -1:
            _close_fd(job_fd)
        if root_fd != -1:
            _close_fd(root_fd)


def parse_range(value: str | None, size: int) -> tuple[int, int] | None:
    if not value:
        return None
    if not value.startswith("bytes=") or "," in value or size <= 0:
        raise InvalidRange
    start_s, sep, end_s = value[6:].partition("-")
    if not sep or (not start_s and not end_s): raise InvalidRange
    try:
        if not start_s:
            length = int(end_s)
            if length <= 0: raise InvalidRange
            return max(0, size - length), size - 1
        start = int(start_s); end = int(end_s) if end_s else size - 1
    except ValueError: raise InvalidRange from None
    if start < 0 or end < start or start >= size: raise InvalidRange
    return start, min(end, size - 1)


def stream(clip: OpenedClip, start: int, end: int) -> Iterator[bytes]:
    if clip.fd is None:
        return
    fd = clip.fd
    remaining = end - start + 1
    try:
        os.lseek(fd, start, os.SEEK_SET)
        while remaining:
            chunk = os.read(fd, min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        close_clip(clip)


def filename(value: str) -> str:
    return value.replace("\\", "_").replace("\r", "").replace("\n", "").replace('"', "") or "clip.mp4"


def media_type(value: str) -> str:
    return mimetypes.guess_type(value)[0] or "application/octet-stream"
