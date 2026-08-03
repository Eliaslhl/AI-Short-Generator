"""
cleanup_old_media.py — periodic retention sweep for generated clips and
orphaned source-video downloads (audit P1-4: neither data/videos/ nor
data/clips/ was ever purged automatically, so storage grew unbounded).

Two independent, best-effort sweeps:

1. Clips retention — data/clips/<job_id>/ for a job whose status is "done"
   or "error" and whose `updated_at` is older than
   settings.clips_retention_days (default 90) is removed. A job still
   "processing" or "pending" is never touched, regardless of age.

2. Orphaned download safety net — data/videos/<job_id>/ and
   video_temp_dir/<job_id>/ directories older than
   settings.orphaned_download_max_age_hours (default 24h) are removed,
   UNLESS a Job row exists for that id with status "processing" (still in
   flight). Source downloads should already be removed immediately after
   every job (backend/api/routes.py, backend/queue/worker.py) — this only
   catches leftovers from a hard crash (kill -9) or anything that predates
   that fix. It intentionally does not touch video_temp_dir/twitch-downloads/
   — that workspace already has its own dedicated cleanup on every run.

Usage (run from the repository root):
    PYTHONPATH=. .venv/bin/python backend/scripts/cleanup_old_media.py
    PYTHONPATH=. .venv/bin/python backend/scripts/cleanup_old_media.py --dry-run

Intended to run on a schedule (Railway Cron Jobs, system cron, etc.) — this
script does not schedule itself, and is safe to run repeatedly / concurrently
with normal job processing (it never touches a "processing" job's directory).
"""

import argparse
import asyncio
import logging
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.config import settings  # noqa: E402
from backend.database import AsyncSessionLocal  # noqa: E402
from backend.models.user import Job  # noqa: E402
from sqlalchemy import select  # noqa: E402

logger = logging.getLogger("cleanup_old_media")


async def _fetch_stale_clip_job_ids(cutoff: datetime) -> list[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Job.id).where(Job.status.in_(("done", "error")), Job.updated_at < cutoff)
        )
        return [row[0] for row in result.all()]


async def _fetch_processing_job_ids() -> set[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Job.id).where(Job.status == "processing"))
        return {row[0] for row in result.all()}


def _remove_dir(path: Path, *, dry_run: bool, reason: str) -> bool:
    if not path.is_dir() or path.is_symlink():
        return False
    logger.info("%s: %s (%s)", "would remove" if dry_run else "removing", path, reason)
    if dry_run:
        return True
    try:
        shutil.rmtree(path)
        return True
    except OSError as exc:
        logger.warning("Failed to remove %s: exception_type=%s", path, type(exc).__name__)
        return False


def sweep_clips(cutoff: datetime, *, dry_run: bool) -> int:
    stale_job_ids = asyncio.run(_fetch_stale_clip_job_ids(cutoff))
    clips_root = Path(settings.clips_dir)
    removed = 0
    for job_id in stale_job_ids:
        candidate = clips_root / job_id
        try:
            candidate = candidate.resolve(strict=False)
        except OSError:
            continue
        if clips_root.resolve(strict=False) not in candidate.parents:
            continue
        if _remove_dir(candidate, dry_run=dry_run, reason=f"clips retention > {settings.clips_retention_days}d"):
            removed += 1
    return removed


def sweep_orphaned_downloads(*, dry_run: bool) -> int:
    processing_job_ids = asyncio.run(_fetch_processing_job_ids())
    max_age_seconds = settings.orphaned_download_max_age_hours * 3600
    now = time.time()
    removed = 0
    for configured_root in (settings.video_dir, settings.video_temp_dir):
        root = Path(configured_root)
        if not root.is_dir():
            continue
        for entry in root.iterdir():
            if not entry.is_dir() or entry.is_symlink():
                continue
            job_id = entry.name
            if job_id in processing_job_ids:
                continue  # still in flight, never touch
            try:
                age_seconds = now - entry.stat().st_mtime
            except OSError:
                continue
            if age_seconds < max_age_seconds:
                continue
            if _remove_dir(
                entry, dry_run=dry_run,
                reason=f"orphaned download > {settings.orphaned_download_max_age_hours}h old",
            ):
                removed += 1
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Log what would be removed without deleting anything.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.clips_retention_days)
    clips_removed = sweep_clips(cutoff, dry_run=args.dry_run)
    downloads_removed = sweep_orphaned_downloads(dry_run=args.dry_run)

    logger.info(
        "Done%s: %s clip director%s, %s orphaned download director%s",
        " (dry run)" if args.dry_run else "",
        clips_removed, "y" if clips_removed == 1 else "ies",
        downloads_removed, "y" if downloads_removed == 1 else "ies",
    )


if __name__ == "__main__":
    main()
