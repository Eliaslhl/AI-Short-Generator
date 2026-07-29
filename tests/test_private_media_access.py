import asyncio
import json
import os

import pytest
from sqlalchemy import select

import backend.api.routes as routes
import backend.services.private_media_service as private_media_service
from backend.config import settings
from backend.models.user import Job
from backend.services.private_media_service import (
    InvalidRange,
    MediaNotFound,
    clip_at,
    open_clip,
    parse_range,
    stream,
    validated_clip_filename,
)
from test_job_authorization import _headers, _seed_users_and_job, http_client


def test_clip_selection_and_ranges():
    clips = '[{"file":"/clips/job/clip_01.mp4"}, {"file":"clip_02.mp4"}]'
    assert clip_at(clips, 1)["file"] == "clip_02.mp4"
    assert parse_range("bytes=0-0", 10) == (0, 0)
    assert parse_range("bytes=-500", 10) == (0, 9)
    assert parse_range("bytes=8-99", 10) == (8, 9)
    for value in ("items=0-1", "bytes=", "bytes=9-1", "bytes=10-", "bytes=0-1,4-5"):
        with pytest.raises(InvalidRange):
            parse_range(value, 10)


def test_invalid_clip_json_is_hidden():
    for value in (None, "[]", "{", "{}"):
        with pytest.raises(MediaNotFound):
            clip_at(value, 0)


def test_historical_reference_validation_requires_an_exact_safe_format():
    assert validated_clip_filename("clip.mp4", "job-a") == "clip.mp4"
    assert validated_clip_filename("/clips/job-a/clip.mp4", "job-a") == "clip.mp4"
    for value in (
        "../secret.mp4", "..\\secret.mp4", "./clip.mp4", "/tmp/clip.mp4",
        "C:\\clip.mp4", "C:/clip.mp4", "/clips/job-b/clip.mp4",
        "/clips/job-a/subdir/clip.mp4", "/clips/job-a/../clip.mp4",
        "https://example.test/clip.mp4", "file:///tmp/clip.mp4",
        "/clips/job-a/clip.mp4?x=1", "/clips/job-a/clip.mp4#part", "clip\n.mp4",
    ):
        with pytest.raises(MediaNotFound):
            validated_clip_filename(value, "job-a")


def test_open_clip_refuses_platforms_without_atomic_nofollow_support(tmp_path, monkeypatch):
    job_dir = tmp_path / "job-a"
    job_dir.mkdir()
    (job_dir / "clip.mp4").write_bytes(b"safe")
    monkeypatch.setattr(private_media_service.os, "O_NOFOLLOW", 0)

    with pytest.raises(MediaNotFound):
        open_clip(str(tmp_path), "job-a", {"file": "clip.mp4"})


def test_open_clip_rejects_symlink_swapped_immediately_before_opening(tmp_path, monkeypatch):
    job_dir = tmp_path / "job-a"
    job_dir.mkdir()
    media = job_dir / "clip.mp4"
    media.write_bytes(b"safe")
    secret = tmp_path / "secret.mp4"
    secret.write_bytes(b"secret")
    real_open = private_media_service.os.open

    def replace_with_symlink(path, flags, *args, **kwargs):
        if path == "clip.mp4" and kwargs.get("dir_fd") is not None:
            media.unlink()
            media.symlink_to(secret)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(private_media_service.os, "open", replace_with_symlink)

    with pytest.raises(MediaNotFound):
        open_clip(str(tmp_path), "job-a", {"file": "clip.mp4"})


def test_open_clip_streams_original_inode_after_name_replacement(tmp_path):
    job_dir = tmp_path / "job-a"
    job_dir.mkdir()
    media = job_dir / "clip.mp4"
    media.write_bytes(b"original")
    opened = open_clip(str(tmp_path), "job-a", {"file": "clip.mp4"})
    replacement = job_dir / "replacement.mp4"
    replacement.write_bytes(b"replacement")
    os.replace(replacement, media)

    fd = opened.fd
    assert b"".join(stream(opened, 0, opened.size - 1)) == b"original"
    assert media.read_bytes() == b"replacement"
    with pytest.raises(OSError):
        os.fstat(fd)


def test_open_clip_streams_unlinked_inode_and_rejects_non_regular_files(tmp_path):
    job_dir = tmp_path / "job-a"
    job_dir.mkdir()
    media = job_dir / "clip.mp4"
    media.write_bytes(b"original")
    opened = open_clip(str(tmp_path), "job-a", {"file": "clip.mp4"})
    media.unlink()

    fd = opened.fd
    assert b"".join(stream(opened, 0, opened.size - 1)) == b"original"
    with pytest.raises(OSError):
        os.fstat(fd)
    (job_dir / "directory.mp4").mkdir()
    with pytest.raises(MediaNotFound):
        open_clip(str(tmp_path), "job-a", {"file": "directory.mp4"})


def test_open_clip_rejects_unsafe_job_ids_and_fifos(tmp_path):
    job_dir = tmp_path / "job-a"
    job_dir.mkdir()
    (job_dir / "clip.mp4").write_bytes(b"safe")
    for job_id in ("", ".", "..", "../job-a", "job-a/child", "job-a\\child"):
        with pytest.raises(MediaNotFound):
            open_clip(str(tmp_path), job_id, {"file": "clip.mp4"})
    fifo = job_dir / "fifo.mp4"
    os.mkfifo(fifo)
    with pytest.raises(MediaNotFound):
        open_clip(str(tmp_path), "job-a", {"file": "fifo.mp4"})


def test_open_clip_rejects_same_directory_symlinks_and_hard_links(tmp_path):
    job_dir = tmp_path / "job-a"
    job_dir.mkdir()
    target = job_dir / "target.mp4"
    target.write_bytes(b"private")
    symlink = job_dir / "linked.mp4"
    try:
        symlink.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(MediaNotFound):
        open_clip(str(tmp_path), "job-a", {"file": "linked.mp4"})
    os.link(target, job_dir / "hard-linked.mp4")
    with pytest.raises(MediaNotFound):
        open_clip(str(tmp_path), "job-a", {"file": "hard-linked.mp4"})


def test_open_clip_rejects_symlinked_job_directory(tmp_path):
    real_job_dir = tmp_path / "real-job"
    real_job_dir.mkdir()
    (real_job_dir / "clip.mp4").write_bytes(b"private")
    try:
        (tmp_path / "job-a").symlink_to(real_job_dir, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(MediaNotFound):
        open_clip(str(tmp_path), "job-a", {"file": "clip.mp4"})


def test_private_media_responses_close_opened_descriptors(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"0123456789")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))
    actual_open_clip = private_media_service.open_clip
    opened = []

    def record_open(*args, **kwargs):
        result = actual_open_clip(*args, **kwargs)
        opened.append((result, result.fd))
        return result

    monkeypatch.setattr(routes, "open_clip", record_open)
    headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    path = f"/api/jobs/{data['job_id']}/clips/0/media"

    assert client.get(path, headers=headers).content == b"0123456789"
    assert client.get(path, headers={**headers, "Range": "bytes=0-0"}).content == b"0"
    assert client.head(path, headers=headers).status_code == 200
    assert client.get(path, headers={**headers, "Range": "bytes=10-"}).status_code == 416
    assert len(opened) == 4
    for opened_clip, fd in opened:
        assert opened_clip.fd is None
        with pytest.raises(OSError):
            os.fstat(fd)


def test_private_media_response_closes_descriptor_when_asgi_streaming_fails(
    tmp_path, monkeypatch
):
    job_dir = tmp_path / "job-a"
    job_dir.mkdir()
    (job_dir / "clip.mp4").write_bytes(b"0123456789")
    opened = open_clip(str(tmp_path), "job-a", {"file": "clip.mp4"})
    fd = opened.fd
    response = routes._PrivateMediaStreamingResponse(
        opened,
        0,
        opened.size - 1,
        media_type="video/mp4",
    )

    async def fail_streaming(*_args, **_kwargs):
        raise OSError("simulated client disconnect")

    monkeypatch.setattr(routes.StreamingResponse, "__call__", fail_streaming)

    with pytest.raises(OSError, match="simulated client disconnect"):
        asyncio.run(
            response(
                {"type": "http", "asgi": {"spec_version": "2.4"}},
                None,
                None,
            )
        )
    assert opened.fd is None
    with pytest.raises(OSError):
        os.fstat(fd)


def test_owner_can_read_private_clip(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    payload = b"0123456789abcdefghijklmnopqrstuvwxyz"
    media.write_bytes(payload)
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-length"] == str(len(payload))
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_other_user_cannot_read_private_clip(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"private-media")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers=_headers(session_factory, data["other_id"], data["other_email"]),
    )

    assert response.status_code == 404
    body = response.text
    assert str(media) not in body
    assert str(tmp_path) not in body
    assert data["owner_id"] not in body
    assert "traceback" not in body.lower()


def test_unauthenticated_user_cannot_read_private_clip(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"private-media")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.get(f"/api/jobs/{data['job_id']}/clips/0/media")

    assert response.status_code == 401
    body = response.text
    assert str(media) not in body
    assert str(tmp_path) not in body
    assert "traceback" not in body.lower()
    assert settings.session_cookie_name not in body


def test_owner_can_head_private_clip(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    payload = b"0123456789abcdefghijklmnopqrstuvwxyz"
    media.write_bytes(payload)
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.head(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["content-length"] == str(len(payload))
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == 'inline; filename="clip.mp4"'


def test_owner_can_read_private_clip_range(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"0123456789")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers={
            **_headers(session_factory, data["owner_id"], data["owner_email"]),
            "Range": "bytes=0-0",
        },
    )

    assert response.status_code == 206
    assert response.content == b"0"
    assert response.headers["content-range"] == "bytes 0-0/10"
    assert response.headers["content-length"] == "1"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "inline" in response.headers["content-disposition"]


def test_owner_can_head_private_clip_range(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"0123456789")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.head(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers={
            **_headers(session_factory, data["owner_id"], data["owner_email"]),
            "Range": "bytes=0-0",
        },
    )

    assert response.status_code == 206
    assert response.content == b""
    assert response.headers["content-range"] == "bytes 0-0/10"
    assert response.headers["content-length"] == "1"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_owner_gets_416_for_unsatisfiable_private_clip_range(
    http_client, tmp_path, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"0123456789")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers={
            **_headers(session_factory, data["owner_id"], data["owner_email"]),
            "Range": "bytes=10-",
        },
    )

    assert response.status_code == 416
    assert response.headers["content-range"] == "bytes */10"
    assert response.headers["accept-ranges"] == "bytes"
    body = response.text
    assert str(media) not in body
    assert str(tmp_path) not in body
    assert "traceback" not in body.lower()
    assert "clips_root" not in body
    assert "/Users/elias" not in body


def test_owner_gets_416_for_unsatisfiable_private_clip_head_range(
    http_client, tmp_path, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"0123456789")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.head(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers={
            **_headers(session_factory, data["owner_id"], data["owner_email"]),
            "Range": "bytes=10-",
        },
    )

    assert response.status_code == 416
    assert response.content == b""
    assert response.headers["content-range"] == "bytes */10"
    assert response.headers["accept-ranges"] == "bytes"


def test_empty_private_clip_has_consistent_get_head_and_range_behavior(
    http_client, tmp_path, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))
    headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    path = f"/api/jobs/{data['job_id']}/clips/0/media"

    get_response = client.get(path, headers=headers)
    head_response = client.head(path, headers=headers)
    range_response = client.get(path, headers={**headers, "Range": "bytes=0-0"})
    head_range_response = client.head(
        path, headers={**headers, "Range": "bytes=0-0"}
    )

    for response in (get_response, head_response):
        assert response.status_code == 200
        assert response.headers["content-length"] == "0"
        assert response.headers["accept-ranges"] == "bytes"
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
    assert get_response.content == b""
    assert head_response.content == b""
    for response in (range_response, head_range_response):
        assert response.status_code == 416
        assert response.content == b""
        assert response.headers["content-range"] == "bytes */0"
        assert response.headers["accept-ranges"] == "bytes"


def test_private_clip_rejects_traversal_reference(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    secret = tmp_path / "secret.mp4"
    secret.write_bytes(b"secret-media-content")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    async def set_dangerous_reference():
        async with session_factory() as session:
            job = await session.scalar(select(Job).where(Job.id == data["job_id"]))
            job.clips_json = json.dumps([{"file": "../secret.mp4"}])
            await session.commit()

    asyncio.run(set_dangerous_reference())
    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 404
    assert response.content != secret.read_bytes()
    body = response.text
    assert str(secret) not in body
    assert str(tmp_path) not in body
    assert "secret.mp4" not in body
    assert "clips_root" not in body
    assert "/Users/elias" not in body
    assert "traceback" not in body.lower()


def test_private_clip_rejects_traversal_even_when_basename_exists(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    secret = tmp_path / data["job_id"] / "secret.mp4"
    secret.parent.mkdir()
    secret.write_bytes(b"same-job-secret")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    async def set_hostile_reference():
        async with session_factory() as session:
            job = await session.scalar(select(Job).where(Job.id == data["job_id"]))
            job.clips_json = json.dumps([{"file": "../secret.mp4"}])
            await session.commit()

    asyncio.run(set_hostile_reference())
    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 404
    assert response.content != secret.read_bytes()
    assert "secret.mp4" not in response.text
    assert "../secret.mp4" not in response.text
    assert str(tmp_path) not in response.text


def test_private_clip_rejects_historical_reference_for_another_job(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    (tmp_path / data["job_id"]).mkdir()
    (tmp_path / data["job_id"] / "clip.mp4").write_bytes(b"job-a")
    other_job_id = "other-job"
    (tmp_path / other_job_id).mkdir()
    (tmp_path / other_job_id / "clip.mp4").write_bytes(b"job-b")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    async def set_other_job_reference():
        async with session_factory() as session:
            job = await session.scalar(select(Job).where(Job.id == data["job_id"]))
            job.clips_json = json.dumps([{"file": f"/clips/{other_job_id}/clip.mp4"}])
            await session.commit()

    asyncio.run(set_other_job_reference())
    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 404
    assert response.content not in (b"job-a", b"job-b")
    assert other_job_id not in response.text


def test_private_clip_rejects_external_symlink(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    external = tmp_path / "external.mp4"
    external.write_bytes(b"external-secret")
    link = tmp_path / data["job_id"] / "linked.mp4"
    link.parent.mkdir()
    try:
        link.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    async def set_symlink_reference():
        async with session_factory() as session:
            job = await session.scalar(select(Job).where(Job.id == data["job_id"]))
            job.clips_json = json.dumps([{"file": "linked.mp4"}])
            await session.commit()

    asyncio.run(set_symlink_reference())
    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 404
    assert response.content != external.read_bytes()
    assert str(external) not in response.text


def test_owner_can_download_private_clip(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    payload = b"0123456789abcdefghijklmnopqrstuvwxyz"
    media.write_bytes(payload)
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media?download=true",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    disposition = response.headers["content-disposition"]
    assert response.status_code == 200
    assert response.content == payload
    assert disposition.startswith("attachment")
    assert 'filename="clip.mp4"' in disposition
    assert response.headers["content-length"] == str(len(payload))
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "/" not in disposition
    assert "\\" not in disposition
    assert "\r" not in disposition
    assert "\n" not in disposition
    assert str(tmp_path) not in disposition


def test_owner_can_read_historical_public_clip_reference(http_client, tmp_path, monkeypatch):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    payload = b"historical-public-clip"
    media.write_bytes(payload)
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))

    async def set_historical_reference():
        async with session_factory() as session:
            job = await session.scalar(select(Job).where(Job.id == data["job_id"]))
            job.clips_json = json.dumps(
                [{"file": f"/clips/{data['job_id']}/clip.mp4"}]
            )
            await session.commit()

    asyncio.run(set_historical_reference())
    response = client.get(
        f"/api/jobs/{data['job_id']}/clips/0/media",
        headers=_headers(session_factory, data["owner_id"], data["owner_email"]),
    )

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-length"] == str(len(payload))
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "inline" in response.headers["content-disposition"]
    assert "/clips/" not in response.text
    assert all("/clips/" not in value for value in response.headers.values())


def test_public_clips_mount_is_unavailable_while_private_route_enforces_access(
    http_client, tmp_path, monkeypatch
):
    client, session_factory = http_client
    data = _seed_users_and_job(session_factory)
    media = tmp_path / data["job_id"] / "clip.mp4"
    media.parent.mkdir()
    payload = b"private-only-media"
    media.write_bytes(payload)
    monkeypatch.setattr(settings, "clips_dir", str(tmp_path))
    owner_headers = _headers(session_factory, data["owner_id"], data["owner_email"])
    other_headers = _headers(session_factory, data["other_id"], data["other_email"])

    public_path = f"/clips/{data['job_id']}/clip.mp4"
    private_path = f"/api/jobs/{data['job_id']}/clips/0/media"
    public_anonymous = client.get(public_path)
    public_owner = client.get(public_path, headers=owner_headers)
    private_anonymous = client.get(private_path)
    private_other = client.get(private_path, headers=other_headers)
    private_owner = client.get(private_path, headers=owner_headers)

    assert public_anonymous.status_code == public_owner.status_code == 404
    assert client.get("/clips/test.mp4").status_code == 404
    assert client.get("/clips/%2e%2e/secret").status_code == 404
    assert private_anonymous.status_code == 401
    assert private_other.status_code == 404
    assert private_owner.status_code == 200
    assert private_owner.content == payload
