from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.jobs import handlers  # noqa: F401  # ensure handlers register themselves
from app.jobs.registry import registry
from app.models import Job

POLL_INTERVAL_SECONDS = 1.0


@asynccontextmanager
async def job_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def fetch_next_job(session: AsyncSession) -> Job | None:
    result = await session.execute(
        select(Job).where(Job.status == "pending").order_by(Job.scheduled_at.nullsfirst(), Job.created_at).limit(1)
    )
    job = result.scalars().first()
    if not job:
        return None
    job.status = "running"
    await session.commit()
    await session.refresh(job)
    return job


async def execute_job(job: Job) -> None:
    handler = registry.get(job.type)
    await handler(job.payload_json)


async def run_once() -> bool:
    async with job_session() as session:
        job = await fetch_next_job(session)
        if not job:
            return False
        try:
            await execute_job(job)
        except Exception as exc:  # pragma: no cover - best effort logging only
            job.status = "failed"
            job.last_error = str(exc)
            job.attempts += 1
        else:
            job.status = "completed"
            job.finished_at = job.finished_at or job.created_at
        finally:
            await session.execute(update(Job).where(Job.id == job.id).values(
                status=job.status,
                last_error=job.last_error,
                attempts=job.attempts,
                finished_at=job.finished_at,
            ))
            await session.commit()
    return True


async def worker_loop() -> None:
    while True:
        has_job = await run_once()
        if not has_job:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


def run_worker() -> None:
    asyncio.run(worker_loop())
