from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_csrf
from ..enums import JobState
from ..models import Job, User
from ..schemas import JobView
from ..scoping import get_owned

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> dict[str, object]:
    rows = list(session.scalars(select(Job).where(Job.owner_id == user.id).order_by(Job.created_at.desc()).limit(100)))
    return {"items": [JobView.model_validate(row).model_dump(mode="json") for row in rows], "total": len(rows), "next_cursor": None}


@router.get("/{job_id}", response_model=JobView)
def get_job(
    job_id: UUID, user: User = Depends(get_current_user), session: Session = Depends(get_db)
) -> Job:
    job = get_owned(session, Job, job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobView, dependencies=[Depends(require_csrf)])
def cancel_job(
    job_id: UUID, user: User = Depends(get_current_user), session: Session = Depends(get_db)
) -> Job:
    job = get_owned(session, Job, job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if not job.cancellable or job.state in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
        raise HTTPException(status_code=409, detail="job cannot be cancelled")
    job.cancellation_requested = True
    job.stage = "cancellation_requested"
    session.commit()
    session.refresh(job)
    return job


