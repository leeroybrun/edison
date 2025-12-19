"""
Path helpers for template composition.

Core guidance must not hardcode repository layout like ".edison" or ".project".
These helpers surface config-driven paths inside prompts/guidelines.
"""
from __future__ import annotations

from edison.core.composition.transformers.base import TransformContext


def _config_str(ctx: TransformContext, path: str, fallback: str = "") -> str:
    value = ctx.get_config(path)
    if value is None:
        return fallback
    rendered = str(value).strip()
    return rendered if rendered else fallback


def project_config_dir(ctx: TransformContext) -> str:
    """Project config directory name (default: .edison)."""
    return _config_str(ctx, "paths.project_config_dir", ".edison")


def project_management_dir(ctx: TransformContext) -> str:
    """Project management root directory (default: .project)."""
    return _config_str(ctx, "project_management_dir", ".project")


def tasks_root(ctx: TransformContext) -> str:
    """Tasks root directory (default: .project/tasks)."""
    return _config_str(ctx, "tasks.paths.root", f"{project_management_dir(ctx)}/tasks")


def qa_root(ctx: TransformContext) -> str:
    """QA root directory (default: .project/qa)."""
    return _config_str(ctx, "tasks.paths.qaRoot", f"{project_management_dir(ctx)}/qa")


def evidence_root(ctx: TransformContext) -> str:
    """Evidence root directory (default: {qaRoot}/validation-evidence)."""
    subdir = _config_str(ctx, "tasks.paths.evidenceSubdir", "validation-evidence")
    return f"{qa_root(ctx)}/{subdir}"


def sessions_root(ctx: TransformContext) -> str:
    """Sessions root directory (default: .project/sessions)."""
    return _config_str(ctx, "session.paths.root", f"{project_management_dir(ctx)}/sessions")


def session_state_dir(ctx: TransformContext, state: str) -> str:
    """Sessions state directory for a logical state (e.g. active/closing/validated)."""
    logical = str(state).strip()
    if not logical:
        return sessions_root(ctx)
    mapped = _config_str(ctx, f"session.states.{logical}", logical)
    return f"{sessions_root(ctx)}/{mapped}"

