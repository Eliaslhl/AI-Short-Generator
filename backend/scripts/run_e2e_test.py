"""Run a local end-to-end pipeline test using an existing sample video.

This script will:
 - create a test user in the DB (if none exists with the test email)
 - create a Job DB record
 - monkeypatch backend.api.routes.download_video to copy a local sample video
   into the job video folder so the pipeline proceeds without contacting YouTube
 - run run_pipeline(job_id, fake_url, user_id, max_clips=2)
 - print the resulting clips and job status

Run from repo root:
  python3 backend/scripts/run_e2e_test.py
"""

import asyncio
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys  # noqa: E402

sys.path.insert(0, str(ROOT))

from backend.config import settings  # noqa: E402
from backend.database import AsyncSessionLocal  # noqa: E402
from backend.models.user import User, Job  # noqa: E402
from sqlalchemy import text  # noqa: E402
import backend.api.routes as routes  # noqa: E402

SAMPLE_VIDEO = None
# pick a representative sample video from settings.video_dir
video_dir = Path(settings.video_dir)
for p in video_dir.rglob("*.mp4"):
    SAMPLE_VIDEO = p
    break

if not SAMPLE_VIDEO:
    print(f"No sample MP4 found under {video_dir}. Place a sample video and retry.")
    raise SystemExit(1)

TEST_EMAIL = "e2e-test@example.local"


async def ensure_user():
    async with AsyncSessionLocal() as db:
        # try find existing user
        res = await db.execute(
            text("SELECT * FROM users WHERE email = :e"), {"e": TEST_EMAIL}
        )
        row = res.first()
        if row:
            # SQLAlchemy returns RowProxy; extract id column depending on schema
            # fallback to query via ORM
            result = await db.execute(
                text("SELECT id FROM users WHERE email = :e"), {"e": TEST_EMAIL}
            )
            user_id = result.scalar_one()
            return user_id

        # create new user via ORM model
        user = User(email=TEST_EMAIL, plan="pro")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user.id


async def create_job_record(user_id: str, youtube_url: str, job_id: str):
    async with AsyncSessionLocal() as db:
        job = Job(
            id=job_id,
            user_id=user_id,
            youtube_url=youtube_url,
            status="pending",
            progress=0,
        )
        db.add(job)
        await db.commit()
        return job


async def run_test():
    user_id = await ensure_user()
    job_id = str(uuid.uuid4())[:8]
    fake_url = "local://sample"

    await create_job_record(user_id, fake_url, job_id)

    # prepare jobs in-memory tracker
    routes.jobs[job_id] = {"status": "pending", "progress": 0, "step": "queued"}

    # monkeypatch download_video to copy SAMPLE_VIDEO into job dir
    def fake_download(youtube_url: str, job_id_arg: str):
        out_dir = Path(settings.video_dir) / job_id_arg
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / SAMPLE_VIDEO.name
        # Use str(...) to satisfy type checkers (shutil stubs expect str/bytes)
        shutil.copy2(str(SAMPLE_VIDEO), str(dest))
        return dest, dest.stem

    routes.download_video = fake_download

    # SAMPLE_VIDEO is guaranteed to be non-None due to the earlier check
    assert SAMPLE_VIDEO is not None
    print(
        f"Starting pipeline test, job_id={job_id}, user_id={user_id}, sample={SAMPLE_VIDEO.name}"
    )

    await routes.run_pipeline(
        job_id,
        fake_url,
        user_id,
        max_clips=2,
        language="",
        subtitle_style="default",
        is_proplus=False,
    )

    print("Pipeline finished. In-memory jobs entry:")
    print(routes.jobs.get(job_id))

    # read DB job result
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            text("SELECT status, clips_json, video_title FROM jobs WHERE id = :id"),
            {"id": job_id},
        )
        row = res.first()
        print("DB job row:", row)


if __name__ == "__main__":
    asyncio.run(run_test())
