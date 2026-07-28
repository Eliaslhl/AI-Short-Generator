"""Safe private clip resolution and byte-range streaming."""
import json
import mimetypes
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


def resolve_clip(clips_root: str, job_id: str, clip: dict) -> Path:
    reference = clip.get("file") or clip.get("path")
    filename_value = validated_clip_filename(reference, job_id)
    job_root = (Path(clips_root) / job_id).resolve()
    raw_candidate = job_root / filename_value
    if raw_candidate.is_symlink():
        raise MediaNotFound
    candidate = raw_candidate.resolve()
    try:
        candidate.relative_to(job_root)
    except ValueError:
        raise MediaNotFound from None
    if not candidate.is_file() or candidate.is_symlink():
        raise MediaNotFound
    return candidate


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


def stream(path: Path, start: int, end: int) -> Iterator[bytes]:
    remaining = end - start + 1
    with path.open("rb") as handle:
        handle.seek(start)
        while remaining:
            chunk = handle.read(min(CHUNK_SIZE, remaining))
            if not chunk: break
            remaining -= len(chunk)
            yield chunk


def filename(path: Path) -> str:
    return path.name.replace("\\", "_").replace("\r", "").replace("\n", "").replace('"', "") or "clip.mp4"


def media_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"
