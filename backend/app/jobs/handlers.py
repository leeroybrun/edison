from __future__ import annotations

import asyncio
from typing import Any

from app.jobs.registry import job


@job("generate_dataset")
async def handle_generate_dataset(payload: dict[str, Any]) -> None:
    await asyncio.sleep(0.01)


@job("execute_batch")
async def handle_execute_batch(payload: dict[str, Any]) -> None:
    await asyncio.sleep(0.01)


@job("judge_outputs")
async def handle_judge_outputs(payload: dict[str, Any]) -> None:
    await asyncio.sleep(0.01)


@job("aggregate_scores")
async def handle_aggregate_scores(payload: dict[str, Any]) -> None:
    await asyncio.sleep(0.01)


@job("refine_prompt")
async def handle_refine_prompt(payload: dict[str, Any]) -> None:
    await asyncio.sleep(0.01)


@job("safety_scan")
async def handle_safety_scan(payload: dict[str, Any]) -> None:
    await asyncio.sleep(0.01)


@job("export_bundle")
async def handle_export_bundle(payload: dict[str, Any]) -> None:
    await asyncio.sleep(0.01)
