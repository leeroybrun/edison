from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Case, Iteration, ModelRun, Output, PromptVersion
from app.schemas.run import ModelRunCreate, ModelRunRead, OutputCreate, OutputRead

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=ModelRunRead, status_code=status.HTTP_201_CREATED)
async def create_run(payload: ModelRunCreate, db: AsyncSession = Depends(get_db)) -> ModelRun:
    prompt = await db.get(PromptVersion, payload.prompt_version_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found")

    run = ModelRun(
        prompt_version_id=payload.prompt_version_id,
        model_id=payload.model_id,
        params_json=payload.params,
        seed=payload.seed,
        started_at=payload.started_at,
        finished_at=payload.finished_at,
        token_in=payload.token_in,
        token_out=payload.token_out,
        cost_usd=payload.cost_usd,
        latency_ms=payload.latency_ms,
        status=payload.status,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{run_id}", response_model=ModelRunRead)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)) -> ModelRun:
    run = await db.get(ModelRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.post("/{run_id}/outputs", response_model=OutputRead, status_code=status.HTTP_201_CREATED)
async def create_output(run_id: int, payload: OutputCreate, db: AsyncSession = Depends(get_db)) -> Output:
    run = await db.get(ModelRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    case = await db.get(Case, payload.case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    output = Output(
        model_run_id=run_id,
        case_id=payload.case_id,
        raw_text=payload.raw_text,
        content_json=payload.content or {},
        tokens_out=payload.tokens_out,
        latency_ms=payload.latency_ms,
        meta_json=payload.meta or {},
    )
    db.add(output)
    await db.commit()
    await db.refresh(output)
    return output


@router.get("/{run_id}/outputs", response_model=list[OutputRead])
async def list_outputs(run_id: int, db: AsyncSession = Depends(get_db)) -> list[Output]:
    run = await db.get(ModelRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    result = await db.execute(select(Output).where(Output.model_run_id == run_id).order_by(Output.created_at))
    return list(result.scalars())
