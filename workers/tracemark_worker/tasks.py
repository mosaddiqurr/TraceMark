"""Bounded job entry points; processing implementations register handlers explicitly."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import dramatiq
from tracemark_api.database import configure_database, make_engine
from tracemark_api.enums import JobState
from tracemark_api.models import Job

from .broker import broker  # noqa: F401

logger = logging.getLogger(__name__)
Handler = Callable[[Job], str | None]
HANDLERS: dict[str, Handler] = {}


def register_handler(kind: str, handler: Handler) -> None:
    if kind in HANDLERS:
        raise ValueError(f"handler already registered for {kind}")
    HANDLERS[kind] = handler


def _execute(job_id: str) -> None:
    engine = make_engine(os.getenv("TRACEMARK_DATABASE_URL", "postgresql+psycopg://tracemark:tracemark@postgres:5432/tracemark"))
    factory = configure_database(engine)
    with factory() as session:
        job = session.get(Job, UUID(job_id))
        if job is None or job.state != JobState.QUEUED:
            return
        if job.cancellation_requested:
            job.state = JobState.CANCELLED
            job.stage = "cancelled"
            job.completed_at = datetime.now(UTC)
            session.commit()
            return
        job.state = JobState.RUNNING
        job.stage = "running"
        job.started_at = datetime.now(UTC)
        session.commit()
        handler = HANDLERS.get(job.kind)
        if handler is None:
            job.state = JobState.FAILED
            job.error_code = "handler_unavailable"
            job.error_message = "processing handler is not installed"
            job.stage = "failed"
            job.completed_at = datetime.now(UTC)
            session.commit()
            return
        try:
            result_url = handler(job)
            session.refresh(job)
            if job.cancellation_requested:
                job.state = JobState.CANCELLED
                job.stage = "cancelled"
            else:
                job.state = JobState.COMPLETED
                job.progress = 100
                job.stage = "completed"
                job.result_url = result_url
            job.completed_at = datetime.now(UTC)
            session.commit()
        except Exception:
            logger.exception("worker job failed", extra={"job_id": job_id, "job_kind": job.kind})
            job.state = JobState.FAILED
            job.stage = "failed"
            job.error_code = "processing_failed"
            job.error_message = "processing failed; inspect server logs with the job identifier"
            job.completed_at = datetime.now(UTC)
            session.commit()
            raise
        finally:
            engine.dispose()


@dramatiq.actor(queue_name="protection", max_retries=2, time_limit=300_000)
def protection_job(job_id: str) -> None:
    _execute(job_id)


@dramatiq.actor(queue_name="verification", max_retries=1, time_limit=300_000)
def verification_job(job_id: str) -> None:
    _execute(job_id)


@dramatiq.actor(queue_name="indexing", max_retries=1, time_limit=600_000)
def indexing_job(job_id: str) -> None:
    _execute(job_id)


@dramatiq.actor(queue_name="scanning", max_retries=1, time_limit=300_000)
def scanning_job(job_id: str) -> None:
    _execute(job_id)


@dramatiq.actor(queue_name="benchmarks", max_retries=0, time_limit=1_800_000)
def benchmark_job(job_id: str) -> None:
    _execute(job_id)


@dramatiq.actor(queue_name="reports", max_retries=1, time_limit=300_000)
def report_job(job_id: str) -> None:
    _execute(job_id)


@dramatiq.actor(queue_name="cleanup", max_retries=1, time_limit=300_000)
def cleanup_job(job_id: str) -> None:
    _execute(job_id)

