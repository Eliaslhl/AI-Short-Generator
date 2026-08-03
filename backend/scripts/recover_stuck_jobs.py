"""
recover_stuck_jobs.py — mark abandoned "processing" jobs as failed and
refund their quota credit (audit P1-2).

If the process handling a job crashes (OOM, kill -9, deploy) between marking
it "processing" and reaching its own error handler, nothing ever marks it
"error" or refunds the quota: it stays "processing" forever, the frontend
polls /status without ever getting a terminal result, and the user's credit
is gone with nothing to show for it.

Detection: Job.updated_at auto-refreshes on every progress update during
healthy processing (SQLAlchemy onupdate=_now on the column) — this only
flags jobs whose updated_at is older than
settings.stuck_job_max_processing_hours (default 6h, well above the 4h
max_source_video_duration_seconds cap), so it should never false-positive on
a merely slow job.

Race-safe by construction: each row is updated via a single conditional
UPDATE (status='processing' AND updated_at < cutoff). If the job's real
pipeline resumes and commits its own progress between the initial query and
this update, the WHERE clause simply matches zero rows and nothing happens —
no read-modify-write gap to race through.

Usage:
    PYTHONPATH=. .venv/bin/python backend/scripts/recover_stuck_jobs.py
    PYTHONPATH=. .venv/bin/python backend/scripts/recover_stuck_jobs.py --dry-run

Intended to run on a schedule (Railway Cron Jobs, etc.), alongside
cleanup_old_media.py — this script does not schedule itself.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, update  # noqa: E402

from backend.api.routes import _decrement_platform_usage, _detect_platform_from_url  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.database import AsyncSessionLocal  # noqa: E402
from backend.models.user import Job, User  # noqa: E402

logger = logging.getLogger("recover_stuck_jobs")

STUCK_JOB_ERROR_MESSAGE = "Processing timed out and could not be recovered."


def _as_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip even for DateTime(timezone=True)
    columns; every timestamp this app writes is UTC (models/user.py::_now),
    so a naive value read back is always UTC, not local time."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


async def _fetch_stuck_job_ids(cutoff: datetime) -> list[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Job.id).where(Job.status == "processing", Job.updated_at < cutoff)
        )
        return [row[0] for row in result.all()]


async def _recover_one(job_id: str, cutoff: datetime, *, dry_run: bool) -> bool:
    """Return True if this job was actually recovered (refunded + marked error)."""
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        if job is None or job.status != "processing" or _as_utc(job.updated_at) >= cutoff:
            return False  # already resolved or resumed since the scan

        if dry_run:
            logger.info("would recover: job_id=%s (stuck since %s)", job_id, job.updated_at)
            return True

        # Conditional UPDATE: only actually transitions the row if it is
        # still exactly the state we scanned for. A concurrent commit from
        # the job's real pipeline changes updated_at (and possibly status),
        # which makes this WHERE clause match zero rows.
        result = await db.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == "processing", Job.updated_at < cutoff)
            .values(status="error", error=STUCK_JOB_ERROR_MESSAGE)
            # This job was already loaded into the session above (db.get),
            # so the ORM's default post-update sync re-evaluates the WHERE
            # clause in Python against that cached object — and SQLite (only
            # in tests; Postgres preserves tz) round-trips updated_at as a
            # naive datetime, which can't compare against the aware cutoff
            # here. Not needed anyway: nothing below re-reads job.status or
            # job.updated_at from the session.
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            await db.rollback()
            logger.info("skipped job_id=%s: no longer stuck by the time of update", job_id)
            return False

        platform = _detect_platform_from_url(job.youtube_url)
        user = await db.get(User, job.user_id)
        if user is not None:
            refunded = _decrement_platform_usage(user, platform)
            if refunded:
                logger.info("refunded %s credit for user_id=%s (job_id=%s)", platform, user.id, job_id)

        await db.commit()
        logger.info("recovered: job_id=%s", job_id)
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Log what would be recovered without changing anything.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.stuck_job_max_processing_hours)
    candidate_ids = asyncio.run(_fetch_stuck_job_ids(cutoff))

    recovered = 0
    for job_id in candidate_ids:
        if asyncio.run(_recover_one(job_id, cutoff, dry_run=args.dry_run)):
            recovered += 1

    logger.info(
        "Done%s: %s/%s stuck job%s recovered",
        " (dry run)" if args.dry_run else "",
        recovered, len(candidate_ids), "" if recovered == 1 else "s",
    )


if __name__ == "__main__":
    main()
