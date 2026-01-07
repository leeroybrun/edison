"""
Path helpers for template composition.

Core guidance must not hardcode repository layout like ".edison" or ".project".
These helpers surface config-driven paths inside prompts/guidelines.
"""
from __future__ import annotations

from pathlib import Path

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
    raw = _config_str(ctx, "tasks.paths.root", f"{project_management_dir(ctx)}/tasks")
    return raw


def qa_root(ctx: TransformContext) -> str:
    """QA root directory (default: .project/qa)."""
    raw = _config_str(ctx, "tasks.paths.qaRoot", f"{project_management_dir(ctx)}/qa")
    return raw


def evidence_root(ctx: TransformContext) -> str:
    """Evidence root directory (default: {qaRoot}/validation-reports)."""
    subdir = _config_str(ctx, "tasks.paths.evidenceSubdir", "validation-reports")
    return f"{qa_root(ctx)}/{subdir}"


def sessions_root(ctx: TransformContext) -> str:
    """Sessions root directory (default: .project/sessions)."""
    raw = _config_str(ctx, "session.paths.root", f"{project_management_dir(ctx)}/sessions")
    return raw


def session_state_dir(ctx: TransformContext, state: str) -> str:
    """Sessions state directory for a logical state (e.g. active/closing/validated)."""
    logical = str(state).strip()
    if not logical:
        return sessions_root(ctx)
    mapped = _config_str(ctx, f"session.states.{logical}", logical)
    return f"{sessions_root(ctx)}/{mapped}"


def task_state_dir(ctx: TransformContext, state: str) -> str:
    """Tasks directory for a semantic state (e.g. todo/wip/done/validated)."""
    from edison.core.config.domains.workflow import WorkflowConfig

    resolved = WorkflowConfig().get_semantic_state("task", str(state).strip().lower())
    return f"{tasks_root(ctx)}/{resolved}"


def qa_state_dir(ctx: TransformContext, state: str) -> str:
    """QA directory for a semantic state (e.g. waiting/todo/wip/done/validated)."""
    from edison.core.config.domains.workflow import WorkflowConfig

    resolved = WorkflowConfig().get_semantic_state("qa", str(state).strip().lower())
    return f"{qa_root(ctx)}/{resolved}"


def _resolve_primary_repo_root(project_root: Path) -> Path:
    """Best-effort resolve the primary checkout root for a git worktree.

    Git worktrees store a `.git` *file* containing `gitdir: <path>` that points at
    `<primary>/.git/worktrees/<id>`. From there, `<primary>/.git` is 2 parents up.
    """
    git = project_root / ".git"
    if git.is_dir():
        return project_root

    if not git.is_file():
        return project_root

    try:
        first = git.read_text(encoding="utf-8").splitlines()[0].strip()
    except Exception:
        return project_root

    if not first.startswith("gitdir:"):
        return project_root

    raw_gitdir = first.split("gitdir:", 1)[1].strip()
    if not raw_gitdir:
        return project_root

    gitdir = Path(raw_gitdir)
    if not gitdir.is_absolute():
        gitdir = (project_root / gitdir).resolve()

    # Typical worktree layout: <primary>/.git/worktrees/<id>
    common_dir = gitdir.parent.parent
    if common_dir.name != ".git":
        return project_root

    return common_dir.parent


def sibling_repo_path(
    ctx: TransformContext,
    repo_name_config_path: str,
    fallback_repo_name: str = "",
) -> str:
    """Resolve a sibling repo path adjacent to the *primary* checkout's parent dir.

    This avoids hardcoding `../some-repo` in templates, which breaks in session
    worktrees where the working directory is nested (e.g. `.worktrees/<session>`).
    """
    repo_name = _config_str(ctx, repo_name_config_path, fallback_repo_name).strip()
    if not repo_name:
        return ""

    root = Path(ctx.project_root) if ctx.project_root else Path.cwd()
    primary_root = _resolve_primary_repo_root(root)
    return str((primary_root.parent / repo_name).resolve())
