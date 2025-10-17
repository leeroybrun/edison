from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Experiment, Project
from app.schemas.experiment import ExperimentCreate, ExperimentRead

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
async def create_experiment(payload: ExperimentCreate, db: AsyncSession = Depends(get_db)) -> Experiment:
    project = await db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    experiment = Experiment(
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
        goal_text=payload.goal_text,
        rubric_json=payload.rubric,
        safety_json=payload.safety or {},
        selector_json=payload.selector or {},
        refiner_json=payload.refiner or {},
        max_iterations=payload.max_iterations,
        budget_tokens=payload.budget_tokens,
        status=payload.status,
    )
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


@router.get("/{experiment_id}", response_model=ExperimentRead)
async def get_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)) -> Experiment:
    experiment = await db.get(Experiment, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment


@router.get("", response_model=list[ExperimentRead])
async def list_experiments(db: AsyncSession = Depends(get_db)) -> list[Experiment]:
    result = await db.execute(select(Experiment).order_by(Experiment.created_at.desc()))
    return list(result.scalars())
