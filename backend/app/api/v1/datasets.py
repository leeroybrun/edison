from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Case, Dataset
from app.schemas.dataset import CaseCreate, CaseRead, DatasetCreate, DatasetRead
from app.schemas.common import Paginated

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def create_dataset(payload: DatasetCreate, db: AsyncSession = Depends(get_db)) -> Dataset:
    dataset = Dataset(
        project_id=payload.project_id,
        name=payload.name,
        kind=payload.kind,
        meta_json=payload.meta,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)) -> Dataset:
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@router.get("", response_model=list[DatasetRead])
async def list_datasets(project_id: int | None = None, db: AsyncSession = Depends(get_db)) -> list[Dataset]:
    stmt = select(Dataset)
    if project_id is not None:
        stmt = stmt.where(Dataset.project_id == project_id)
    result = await db.execute(stmt.order_by(Dataset.created_at.desc()))
    return list(result.scalars())


@router.post("/{dataset_id}/cases", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def add_case(dataset_id: int, payload: CaseCreate, db: AsyncSession = Depends(get_db)) -> Case:
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    case = Case(
        dataset_id=dataset_id,
        input_json=payload.input,
        expected_json=payload.expected or {},
        tags=payload.tags,
        difficulty=payload.difficulty,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


@router.get("/{dataset_id}/cases", response_model=Paginated)
async def list_cases(
    dataset_id: int,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
) -> Paginated:
    stmt = select(Case).where(Case.dataset_id == dataset_id).offset(offset).limit(limit + 1)
    result = await db.execute(stmt)
    items = list(result.scalars())
    total = len(items)
    if total > limit:
        items = items[:limit]
        total = offset + limit + 1
    return Paginated(items=items, total=total)


@router.post("/{dataset_id}/upload")
async def upload_dataset(dataset_id: int, file: UploadFile, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    # In v1 we simply acknowledge upload - actual ingestion handled offline
    contents = await file.read()
    dataset.meta_json.setdefault("uploads", []).append({"filename": file.filename, "size": len(contents)})
    await db.commit()
    return {"status": "received"}
