"""Deterministic session context payload for hooks and tooling.

This module provides a small, stable "context refresher" payload intended for:
- Claude Code hooks (SessionStart, PreCompact, UserPromptSubmit)
- Human inspection (`edison session context`)
- Reuse by orchestrator-centric tooling (`edison session next`)

Design goals:
- Deterministic output (stable ordering; no timestamps)
- Safe to call outside Edison projects (silent no-op in text mode)
- Config-driven (avoid hardcoded paths/state lists)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from edison.core.utils.paths.project import get_project_config_dir


def _load_session_context_config(project_root: Path) -> dict[str, Any]:
    """Load session context configuration (best-effort, fail-open)."""
    try:
        from edison.core.config.domains.session import SessionConfig

        sess = SessionConfig(repo_root=project_root)
        ctx = sess.section.get("context", {})
        return ctx if isinstance(ctx, dict) else {}
    except Exception:
        return {}


def _normalize_field_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _get_payload_fields(project_root: Path) -> list[str]:
    cfg = _load_session_context_config(project_root)
    payload = cfg.get("payload", {}) if isinstance(cfg.get("payload", {}), dict) else {}
    fields = _normalize_field_list(payload.get("fields"))
    return fields


def _get_render_config(project_root: Path, *, target: str) -> tuple[bool, str, list[str]]:
    """Return (enabled, heading, fields) for a render target (markdown|next)."""
    cfg = _load_session_context_config(project_root)
    render = cfg.get("render", {}) if isinstance(cfg.get("render", {}), dict) else {}
    spec = render.get(target, {}) if isinstance(render.get(target, {}), dict) else {}

    enabled = bool(spec.get("enabled", True))
    heading = str(spec.get("heading") or ("## Edison Context" if target == "markdown" else "Edison Context:"))
    fields = _normalize_field_list(spec.get("fields"))
    return enabled, heading, fields


@dataclass(frozen=True)
class SessionContextPayload:
    """Structured context snapshot for a project/session."""

    is_edison_project: bool
    project_root: Path
    session_id: str | None
    session_state: str | None = None
    worktree_path: str | None = None
    current_task_id: str | None = None
    current_task_state: str | None = None
    active_packs: tuple[str, ...] = ()
    # Actor identity fields (from resolve_actor_identity)
    actor_kind: str | None = None
    actor_id: str | None = None
    actor_constitution: str | None = None
    actor_read_cmd: str | None = None
    actor_resolution: str | None = None

    def to_dict(self) -> dict[str, Any]:
        fields = _get_payload_fields(self.project_root) if self.is_edison_project else []
        include_all = not bool(fields)
        include = set(fields)

        base: dict[str, Any] = {}

        def _put(key: str, value: Any) -> None:
            if include_all or key in include:
                base[key] = value

        # Always present core identity fields (hook-safe tooling relies on these).
        base["isEdisonProject"] = self.is_edison_project
        base["projectRoot"] = str(self.project_root)
        base["sessionId"] = self.session_id

        _put("sessionState", self.session_state)
        _put("worktreePath", self.worktree_path)
        _put("currentTaskId", self.current_task_id)
        _put("currentTaskState", self.current_task_state)
        _put("activePacks", list(self.active_packs))

        if self.is_edison_project and (include_all or "constitutions" in include):
            try:
                cfg_dir = get_project_config_dir(self.project_root, create=False)
                const_dir = cfg_dir / "_generated" / "constitutions"
                base["constitutions"] = {
                    "agents": str(const_dir / "AGENTS.md"),
                    "orchestrator": str(const_dir / "ORCHESTRATOR.md"),
                    "validators": str(const_dir / "VALIDATORS.md"),
                }
            except Exception:
                pass

        # Actor identity fields (always included for Edison projects)
        if self.is_edison_project:
            _put("actorKind", self.actor_kind or "unknown")
            if self.actor_id:
                _put("actorId", self.actor_id)
            if self.actor_constitution:
                _put("actorConstitution", self.actor_constitution)
            if self.actor_read_cmd:
                _put("actorReadCmd", self.actor_read_cmd)
            _put("actorResolution", self.actor_resolution or "fallback")

        return base


def _is_edison_project(project_root: Path) -> bool:
    """Best-effort detection for whether a path is an Edison project."""
    try:
        cfg_dir = get_project_config_dir(project_root, create=False)
        if cfg_dir.exists():
            return True
    except Exception:
        pass

    # Fall back to common management dir marker without forcing config loads.
    if (project_root / ".project").exists():
        return True
    return False


def build_session_context_payload(
    *,
    project_root: Path,
    session_id: str | None = None,
) -> SessionContextPayload:
    """Build a deterministic context snapshot for the current project."""
    if not _is_edison_project(project_root):
        return SessionContextPayload(
            is_edison_project=False,
            project_root=project_root,
            session_id=None,
        )

    session_state: str | None = None
    worktree_path: str | None = None
    if session_id:
        try:
            from edison.core.session.persistence.repository import SessionRepository

            repo = SessionRepository(project_root=project_root)
            entity = repo.get(session_id)
            if entity is not None:
                session_state = str(entity.state or "") or None
                worktree_path = (
                    (entity.git.worktree_path if entity.git else None)
                    or None
                )
        except Exception:
            # Fail-open: context hooks must never crash due to session storage issues.
            session_state = None
            worktree_path = None

    active_packs: tuple[str, ...] = ()
    try:
        from edison.core.config import ConfigManager

        full = ConfigManager(repo_root=project_root).load_config(
            validate=False,
            include_packs=True,
        )
        packs = full.get("packs", {}) if isinstance(full.get("packs", {}), dict) else {}
        raw_active = packs.get("active", [])
        if isinstance(raw_active, list):
            active_packs = tuple(str(p) for p in raw_active if str(p).strip())
    except Exception:
        active_packs = ()

    current_task_id: str | None = None
    current_task_state: str | None = None
    if session_id:
        try:
            from edison.core.config.domains.workflow import WorkflowConfig
            from edison.core.task.repository import TaskRepository

            workflow = WorkflowConfig(repo_root=project_root)
            wip_state = str(workflow.get_semantic_state("task", "wip"))
            candidates = TaskRepository(project_root=project_root).list_by_state(wip_state)
            owned = [t for t in candidates if getattr(t, "session_id", None) == session_id]
            if len(owned) == 1:
                current_task_id = str(owned[0].id)
                current_task_state = str(owned[0].state)
        except Exception:
            current_task_id = None
            current_task_state = None

    # Resolve actor identity (fail-open)
    actor_kind: str | None = None
    actor_id_resolved: str | None = None
    actor_constitution: str | None = None
    actor_read_cmd: str | None = None
    actor_resolution: str | None = None
    try:
        from edison.core.actor.identity import resolve_actor_identity

        actor = resolve_actor_identity(project_root=project_root, session_id=session_id)
        actor_kind = actor.kind
        actor_id_resolved = actor.actor_id
        actor_constitution = str(actor.constitution_path) if actor.constitution_path else None
        actor_read_cmd = actor.read_command
        actor_resolution = actor.source
    except Exception:
        # Fail-open: actor identity resolution should never crash context building
        actor_kind = "unknown"
        actor_resolution = "fallback"

    return SessionContextPayload(
        is_edison_project=True,
        project_root=project_root,
        session_id=session_id,
        session_state=session_state,
        worktree_path=worktree_path,
        current_task_id=current_task_id,
        current_task_state=current_task_state,
        active_packs=active_packs,
        actor_kind=actor_kind,
        actor_id=actor_id_resolved,
        actor_constitution=actor_constitution,
        actor_read_cmd=actor_read_cmd,
        actor_resolution=actor_resolution,
    )


def format_session_context_markdown(payload: SessionContextPayload) -> str:
    """Render a compact, deterministic Markdown context block."""
    if not payload.is_edison_project:
        return ""

    enabled, heading, fields = _get_render_config(payload.project_root, target="markdown")
    if not enabled:
        return ""
    if not fields:
        return ""

    lines: list[str] = []
    lines.append(heading)
    lines.append("")

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(payload.project_root))
        except Exception:
            return str(p)

    for field in fields:
        if field == "projectRoot":
            lines.append(f"- Project: `{payload.project_root}`")
        elif field == "constitutions":
            try:
                cfg_dir = get_project_config_dir(payload.project_root, create=False)
                const_dir = cfg_dir / "_generated" / "constitutions"
                lines.append(f"- Constitution (Agent): `{_rel(const_dir / 'AGENTS.md')}`")
                lines.append(f"- Constitution (Orchestrator): `{_rel(const_dir / 'ORCHESTRATOR.md')}`")
                lines.append(f"- Constitution (Validator): `{_rel(const_dir / 'VALIDATORS.md')}`")
            except Exception:
                # Fail-open: hooks must not crash due to filesystem drift.
                pass
        elif field == "session":
            if payload.session_id:
                if payload.session_state:
                    lines.append(f"- Session: `{payload.session_id}` (state: `{payload.session_state}`)")
                else:
                    lines.append(f"- Session: `{payload.session_id}`")
        elif field == "loopDriver":
            if payload.session_id:
                lines.append(f"- Loop driver: `edison session next {payload.session_id}`")
        elif field == "worktreePath":
            if payload.worktree_path:
                lines.append(f"- Worktree: `{payload.worktree_path}`")
        elif field == "currentTask":
            if payload.current_task_id:
                if payload.current_task_state:
                    lines.append(
                        f"- Current Task: `{payload.current_task_id}` (state: `{payload.current_task_state}`)"
                    )
                else:
                    lines.append(f"- Current Task: `{payload.current_task_id}`")
        elif field == "activePacks":
            if payload.active_packs:
                packs = ", ".join(f"`{p}`" for p in payload.active_packs)
                lines.append(f"- Active Packs: {packs}")
        elif field == "actor":
            # Actor identity stanza
            if payload.actor_kind:
                if payload.actor_id:
                    lines.append(f"- Actor: `{payload.actor_kind}` (`{payload.actor_id}`)")
                else:
                    lines.append(f"- Actor: `{payload.actor_kind}`")
                if payload.actor_read_cmd:
                    lines.append(f"- Re-read constitution: `{payload.actor_read_cmd}`")
    lines.append("")
    return "\n".join(lines)


def format_session_context_for_next(ctx: dict[str, Any]) -> list[str]:
    """Render a stable, human-readable context block for `session next` output.

    This intentionally shares semantics with `format_session_context_markdown`,
    but is formatted as a simple bullet list (not Markdown headings) to match
    the `session next` output style.
    """
    if not isinstance(ctx, dict) or not ctx.get("isEdisonProject"):
        return []

    lines: list[str] = []
    project_root_raw = ctx.get("projectRoot")
    project_root: Path | None = None
    if isinstance(project_root_raw, str) and project_root_raw.strip():
        try:
            project_root = Path(project_root_raw)
        except Exception:
            project_root = None

    enabled = True
    heading = "Edison Context:"
    fields: list[str] = []
    if project_root is not None:
        enabled, heading, fields = _get_render_config(project_root, target="next")
    if not enabled or not fields:
        return []

    lines.append(heading)

    def _rel(p: Path) -> str:
        if project_root is None:
            return str(p)
        try:
            return str(p.relative_to(project_root))
        except Exception:
            return str(p)

    for field in fields:
        if field == "projectRoot":
            if isinstance(project_root_raw, str) and project_root_raw.strip():
                lines.append(f"  - Project: {project_root_raw}")
        elif field == "constitutions":
            # Constitution pointers (best-effort).
            if project_root is not None:
                try:
                    cfg_dir = get_project_config_dir(project_root, create=False)
                    const_dir = cfg_dir / "_generated" / "constitutions"
                    lines.append(f"  - Constitution (Agent): {_rel(const_dir / 'AGENTS.md')}")
                    lines.append(f"  - Constitution (Orchestrator): {_rel(const_dir / 'ORCHESTRATOR.md')}")
                    lines.append(f"  - Constitution (Validator): {_rel(const_dir / 'VALIDATORS.md')}")
                except Exception:
                    pass
        elif field == "session":
            session_id = ctx.get("sessionId")
            if isinstance(session_id, str) and session_id.strip():
                state = ctx.get("sessionState")
                if isinstance(state, str) and state.strip():
                    lines.append(f"  - Session: {session_id} (state: {state})")
                else:
                    lines.append(f"  - Session: {session_id}")
        elif field == "loopDriver":
            session_id = ctx.get("sessionId")
            if isinstance(session_id, str) and session_id.strip():
                lines.append(f"  - Loop driver: edison session next {session_id}")
        elif field == "worktreePath":
            worktree = ctx.get("worktreePath")
            if isinstance(worktree, str) and worktree.strip():
                lines.append(f"  - Worktree: {worktree}")
        elif field == "currentTask":
            task_id = ctx.get("currentTaskId")
            if isinstance(task_id, str) and task_id.strip():
                st = ctx.get("currentTaskState")
                if isinstance(st, str) and st.strip():
                    lines.append(f"  - Current Task: {task_id} (state: {st})")
                else:
                    lines.append(f"  - Current Task: {task_id}")
        elif field == "activePacks":
            packs = ctx.get("activePacks") or []
            if isinstance(packs, list) and packs:
                lines.append(f"  - Active Packs: {', '.join(str(p) for p in packs)}")
        elif field == "actor":
            # Actor identity stanza
            actor_kind = ctx.get("actorKind")
            if isinstance(actor_kind, str) and actor_kind.strip():
                actor_id = ctx.get("actorId")
                if isinstance(actor_id, str) and actor_id.strip():
                    lines.append(f"  - Actor: {actor_kind} ({actor_id})")
                else:
                    lines.append(f"  - Actor: {actor_kind}")
                read_cmd = ctx.get("actorReadCmd")
                if isinstance(read_cmd, str) and read_cmd.strip():
                    lines.append(f"  - Re-read constitution: {read_cmd}")

    lines.append("")
    return lines


__all__ = [
    "SessionContextPayload",
    "build_session_context_payload",
    "format_session_context_markdown",
    "format_session_context_for_next",
]
