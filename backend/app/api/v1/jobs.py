from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Job
from app.schemas.job import JobCreate, JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)) -> Job:
    job = Job(
        type=payload.type,
        payload_json=payload.payload,
        status=payload.status,
        scheduled_at=payload.scheduled_at,
        started_at=payload.started_at,
        finished_at=payload.finished_at,
        attempts=payload.attempts,
        last_error=payload.last_error,
        worker_id=payload.worker_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)) -> Job:
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("", response_model=list[JobRead])
async def list_jobs(status_filter: str | None = None, db: AsyncSession = Depends(get_db)) -> list[Job]:
    stmt = select(Job)
    if status_filter:
        stmt = stmt.where(Job.status == status_filter)
    result = await db.execute(stmt.order_by(Job.created_at.desc()))
    return list(result.scalars())
