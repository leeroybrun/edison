"""Memory pipelines (event-driven).

Pipelines allow Edison to:
- extract a structured session insights record
- persist it to one or more providers
- optionally run provider indexing commands
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from edison.core.config import ConfigManager
from edison.core.memory import MemoryManager


@dataclass(frozen=True)
class MemoryPipelineStepError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _load_pipeline_config(*, project_root: Path, strict: bool) -> dict[str, Any]:
    cfg = ConfigManager(repo_root=project_root).load_config(validate=bool(strict), include_packs=True)
    mem = cfg.get("memory", {}) if isinstance(cfg.get("memory", {}), dict) else {}
    pipelines = mem.get("pipelines", {}) if isinstance(mem.get("pipelines", {}), dict) else {}
    return pipelines


def _get_step_vars(step: dict[str, Any]) -> tuple[str | None, str | None]:
    in_var = step.get("inputVar")
    out_var = step.get("outputVar")
    return (
        str(in_var) if isinstance(in_var, str) and in_var.strip() else None,
        str(out_var) if isinstance(out_var, str) and out_var.strip() else None,
    )


def run_memory_pipelines(
    *,
    project_root: Path,
    event: str,
    session_id: str,
    strict: bool = False,
) -> None:
    """Run configured memory pipelines for a given event."""
    pipelines = _load_pipeline_config(project_root=project_root, strict=strict)
    pipe = pipelines.get(str(event))
    if not isinstance(pipe, dict) or pipe.get("enabled") is False:
        return
    steps = pipe.get("steps", [])
    if not isinstance(steps, list):
        if strict:
            raise MemoryPipelineStepError(f"memory.pipelines.{event}.steps must be a list")
        return

    mgr = MemoryManager(project_root=project_root, validate_config=bool(strict))
    providers_by_id = {getattr(p, "id", ""): p for p in mgr.providers if getattr(p, "id", "")}

    vars: dict[str, Any] = {}

    for step in steps:
        if not isinstance(step, dict):
            if strict:
                raise MemoryPipelineStepError(f"memory.pipelines.{event}.steps entries must be objects")
            continue

        kind = str(step.get("kind") or "").strip()
        in_var, out_var = _get_step_vars(step)

        if kind == "session-insights-v1":
            from edison.core.memory.insights import extract_session_insights_v1

            record = extract_session_insights_v1(project_root=project_root, session_id=session_id)
            vars[out_var or "insights"] = record
            continue

        if kind == "provider-save-structured":
            provider_id = str(step.get("provider") or "").strip()
            if not provider_id:
                if strict:
                    raise MemoryPipelineStepError("provider-save-structured requires provider")
                continue
            provider = providers_by_id.get(provider_id)
            if provider is None:
                if strict:
                    raise MemoryPipelineStepError(f"Unknown provider '{provider_id}'")
                continue
            if not in_var or in_var not in vars:
                if strict:
                    raise MemoryPipelineStepError("provider-save-structured requires inputVar bound in vars")
                continue
            record = vars.get(in_var)
            if not isinstance(record, dict):
                if strict:
                    raise MemoryPipelineStepError("provider-save-structured inputVar must be a mapping")
                continue
            try:
                fn = getattr(provider, "save_structured", None)
                if callable(fn):
                    fn(record, session_id=session_id)
                else:
                    mgr.save_structured(record, session_id=session_id)
            except Exception:
                if strict:
                    raise
            continue

        if kind == "provider-save-text":
            provider_id = str(step.get("provider") or "").strip()
            if not provider_id:
                if strict:
                    raise MemoryPipelineStepError("provider-save-text requires provider")
                continue
            provider = providers_by_id.get(provider_id)
            if provider is None:
                if strict:
                    raise MemoryPipelineStepError(f"Unknown provider '{provider_id}'")
                continue
            if not in_var or in_var not in vars:
                if strict:
                    raise MemoryPipelineStepError("provider-save-text requires inputVar bound in vars")
                continue
            text = vars.get(in_var)
            if not isinstance(text, str):
                if strict:
                    raise MemoryPipelineStepError("provider-save-text inputVar must be a string")
                continue
            try:
                provider.save(text, session_id=session_id)
            except Exception:
                if strict:
                    raise
            continue

        if kind == "provider-index":
            provider_id = str(step.get("provider") or "").strip()
            if not provider_id:
                if strict:
                    raise MemoryPipelineStepError("provider-index requires provider")
                continue
            provider = providers_by_id.get(provider_id)
            if provider is None:
                if strict:
                    raise MemoryPipelineStepError(f"Unknown provider '{provider_id}'")
                continue
            try:
                fn = getattr(provider, "index", None)
                if callable(fn):
                    fn(event=event, session_id=session_id)
            except Exception:
                if strict:
                    raise
            continue

        if strict:
            raise MemoryPipelineStepError(f"Unknown memory pipeline step kind '{kind}'")


__all__ = ["run_memory_pipelines", "MemoryPipelineStepError"]

