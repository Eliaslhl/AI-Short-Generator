"""Centralized ownership checks for persisted and queued jobs."""

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import Job, User
from backend.queue.redis_queue import QueueBackendUnavailableError


class JobAccessService:
    """Resolve jobs for their owner without revealing other users' jobs."""

    not_found_detail = "Job not found"

    async def get_owned_job(
        self, db: AsyncSession, job_id: str, user: User
    ) -> Job | None:
        """Return a persisted job only when it belongs to ``user``."""
        result = await db.execute(
            select(Job).where(Job.id == job_id, Job.user_id == user.id)
        )
        return result.scalar_one_or_none()

    async def require_owned_job(
        self, db: AsyncSession, job_id: str, user: User
    ) -> Job:
        """Return an owned job or the same 404 used for a missing job."""
        job = await self.get_owned_job(db, job_id, user)
        if job is None:
            raise HTTPException(status_code=404, detail=self.not_found_detail)
        return job

    def get_owned_memory_job(
        self, job: Job, memory_jobs: Mapping[str, dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Read transient state only after the database has proven ownership."""
        return memory_jobs.get(job.id)

    def require_owned_rq_job(self, queue: Any, job_id: str, user: User) -> Any:
        """Return an RQ job only when its persisted owner metadata matches."""
        try:
            rq_job = queue.get_rq_job(job_id)
        except QueueBackendUnavailableError as exc:
            raise HTTPException(
                status_code=503, detail="Job service unavailable"
            ) from exc
        metadata = getattr(rq_job, "meta", None) if rq_job is not None else None
        owner_id = metadata.get("user_id") if isinstance(metadata, Mapping) else None

        if owner_id != user.id:
            raise HTTPException(status_code=404, detail=self.not_found_detail)
        return rq_job


job_access_service = JobAccessService()
