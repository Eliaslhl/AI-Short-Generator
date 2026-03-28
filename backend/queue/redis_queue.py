"""
redis_queue.py – Redis-based job queue for async video processing.

Supports both RQ (Redis Queue) and Celery backends.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Queue backend selection
QUEUE_BACKEND = os.getenv("QUEUE_BACKEND", "rq")  # "rq" or "celery"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class JobStatus(str, Enum):
    """Job status states."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueueJob:
    """Represents a queued job for video processing."""
    
    def __init__(
        self,
        job_id: str,
        func_name: str,
        args: tuple = (),
        kwargs: dict = None,
        status: JobStatus = JobStatus.PENDING,
        progress: int = 0,
        step: str = "Queued...",
        result: dict = None,
        error: str = None,
    ):
        self.job_id = job_id
        self.func_name = func_name
        self.args = args
        self.kwargs = kwargs or {}
        self.status = status
        self.progress = progress
        self.step = step
        self.result = result
        self.error = error
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "job_id": self.job_id,
            "func_name": self.func_name,
            "status": self.status.value,
            "progress": self.progress,
            "step": self.step,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RedisQueue:
    """Redis-based job queue for async processing."""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.backend = QUEUE_BACKEND
        self._init_backend()

    def _init_backend(self):
        """Initialize the queue backend."""
        if self.backend == "rq":
            self._init_rq()
        elif self.backend == "celery":
            self._init_celery()
        else:
            raise ValueError(f"Unknown queue backend: {self.backend}")

    def _init_rq(self):
        """Initialize RQ (Redis Queue)."""
        try:
            import redis
            from rq import Queue
            
            self.redis_conn = redis.from_url(self.redis_url)
            self.queue = Queue(connection=self.redis_conn)
            logger.info("✅ RQ queue initialized")
        except ImportError:
            logger.error("❌ RQ not installed. Install with: pip install rq redis")
            raise

    def _init_celery(self):
        """Initialize Celery."""
        try:
            from celery import Celery
            
            self.celery_app = Celery(
                "video_processor",
                broker=self.redis_url,
                backend=self.redis_url,
            )
            self.celery_app.conf.update(
                task_serializer="json",
                accept_content=["json"],
                result_serializer="json",
                timezone="UTC",
                enable_utc=True,
            )
            logger.info("✅ Celery queue initialized")
        except ImportError:
            logger.error("❌ Celery not installed. Install with: pip install celery")
            raise

    def enqueue(
        self,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Enqueue a job."""
        if self.backend == "rq":
            return self._enqueue_rq(func, *args, job_id=job_id, **kwargs)
        else:
            return self._enqueue_celery(func, *args, job_id=job_id, **kwargs)

    def _enqueue_rq(
        self,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Enqueue a job with RQ."""
        from rq.job import Job
        
        job = self.queue.enqueue(func, *args, job_id=job_id, **kwargs)
        logger.info(f"📨 Enqueued RQ job: {job.id}")
        return job.id

    def _enqueue_celery(
        self,
        func: Callable,
        *args,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Enqueue a job with Celery."""
        task = self.celery_app.send_task(
            func.__name__,
            args=args,
            kwargs=kwargs,
            task_id=job_id,
        )
        logger.info(f"📨 Enqueued Celery task: {task.id}")
        return task.id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        if self.backend == "rq":
            return self._get_job_status_rq(job_id)
        else:
            return self._get_job_status_celery(job_id)

    def _get_job_status_rq(self, job_id: str) -> Dict[str, Any]:
        """Get RQ job status."""
        from rq.job import Job
        
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            return {
                "job_id": job_id,
                "status": job.get_status(),
                "progress": getattr(job.meta, "progress", 0),
                "step": getattr(job.meta, "step", "Processing..."),
                "result": job.result if job.is_finished else None,
                "error": str(job.exc_info) if job.is_failed else None,
            }
        except Exception as e:
            logger.error(f"❌ Error fetching RQ job {job_id}: {e}")
            return {
                "job_id": job_id,
                "status": "unknown",
                "error": str(e),
            }

    def _get_job_status_celery(self, job_id: str) -> Dict[str, Any]:
        """Get Celery task status."""
        result = self.celery_app.AsyncResult(job_id)
        return {
            "job_id": job_id,
            "status": result.state,
            "progress": result.info.get("progress", 0) if isinstance(result.info, dict) else 0,
            "step": result.info.get("step", "Processing...") if isinstance(result.info, dict) else "Processing...",
            "result": result.result if result.state == "SUCCESS" else None,
            "error": str(result.info) if result.state == "FAILURE" else None,
        }

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        if self.backend == "rq":
            return self._cancel_job_rq(job_id)
        else:
            return self._cancel_job_celery(job_id)

    def _cancel_job_rq(self, job_id: str) -> bool:
        """Cancel an RQ job."""
        from rq.job import Job
        
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.cancel()
            logger.info(f"❌ Cancelled RQ job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error cancelling RQ job {job_id}: {e}")
            return False

    def _cancel_job_celery(self, job_id: str) -> bool:
        """Cancel a Celery task."""
        try:
            self.celery_app.control.revoke(job_id, terminate=True)
            logger.info(f"❌ Cancelled Celery task: {job_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error cancelling Celery task {job_id}: {e}")
            return False


# Global queue instance
_queue_instance: Optional[RedisQueue] = None


def get_queue() -> RedisQueue:
    """Get or create the global queue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = RedisQueue(REDIS_URL)
    return _queue_instance
