from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import datasets, experiments, hitl, jobs, projects, prompts, runs

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(experiments.router)
api_router.include_router(datasets.router)
api_router.include_router(prompts.router)
api_router.include_router(runs.router)
api_router.include_router(hitl.router)
api_router.include_router(jobs.router)
