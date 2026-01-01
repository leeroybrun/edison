"""External sync actions for state machine transitions.

These actions keep external spec artifacts (e.g. Spec Kit / OpenSpec tasks.md)
in sync with Edison task state without making those systems authoritative for
Edison workflow.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, MutableMapping


_SPECKIT_TASK_LINE = re.compile(r"^(\s*-\s*\[)([ xX])(\]\s*)(T\d+)(\b.*)$")
_CHECKBOX_LINE = re.compile(r"^(\s*-\s*\[)([ xX])(\])(\s+.*)$")


def sync_external_task_sources(ctx: MutableMapping[str, Any]) -> None:
    """Best-effort sync of external task checklists on task validation.

    Config-driven and fail-open by default. If a task has no integration metadata,
    this is a no-op.
    """
    if str(ctx.get("entity_type") or "").strip().lower() != "task":
        return

    project_root_raw = ctx.get("project_root")
    if not project_root_raw:
        return
    project_root = Path(str(project_root_raw))

    cfg = _get_external_sync_config(project_root)
    if not cfg.get("enabled", True):
        return
    if not cfg.get("onTaskValidated", True):
        return

    task_payload = ctx.get("task", {})
    if not isinstance(task_payload, MutableMapping):
        return

    integration = task_payload.get("integration") or {}
    if not isinstance(integration, MutableMapping):
        return

    kind = str(integration.get("kind") or "").strip().lower()
    if kind == "speckit":
        # Dispatch via registry so packs/projects can override only the Speckit sync behavior
        # without replacing the whole router action.
        from edison.core.state import action_registry

        action_registry.execute("sync_speckit_task_sources", ctx)
        return
    if kind == "openspec":
        from edison.core.state import action_registry

        action_registry.execute("sync_openspec_task_sources", ctx)
        return


def sync_speckit_task_sources(ctx: MutableMapping[str, Any]) -> None:
    """Sync Spec Kit `tasks.md` for the validated Edison task (if configured)."""
    project_root = _project_root_from_ctx(ctx)
    if project_root is None:
        return
    cfg = _get_external_sync_config(project_root)
    if not cfg.get("enabled", True) or not cfg.get("onTaskValidated", True):
        return
    task_payload = ctx.get("task", {})
    if not isinstance(task_payload, MutableMapping):
        return
    integration = task_payload.get("integration") or {}
    if not isinstance(integration, MutableMapping):
        return
    _sync_speckit_impl(
        ctx, integration, project_root=project_root, cfg=cfg.get("speckit", {})
    )


def sync_openspec_task_sources(ctx: MutableMapping[str, Any]) -> None:
    """Sync OpenSpec `tasks.md` for the validated Edison task (if configured)."""
    project_root = _project_root_from_ctx(ctx)
    if project_root is None:
        return
    cfg = _get_external_sync_config(project_root)
    if not cfg.get("enabled", True) or not cfg.get("onTaskValidated", True):
        return
    task_payload = ctx.get("task", {})
    if not isinstance(task_payload, MutableMapping):
        return
    integration = task_payload.get("integration") or {}
    if not isinstance(integration, MutableMapping):
        return
    _sync_openspec_impl(
        ctx, integration, project_root=project_root, cfg=cfg.get("openspec", {})
    )


def _project_root_from_ctx(ctx: MutableMapping[str, Any]) -> Path | None:
    project_root_raw = ctx.get("project_root")
    if not project_root_raw:
        return None
    try:
        return Path(str(project_root_raw))
    except Exception:
        return None


def _sync_speckit_impl(
    ctx: MutableMapping[str, Any],
    integration: MutableMapping[str, Any],
    *,
    project_root: Path,
    cfg: MutableMapping[str, Any],
) -> None:
    speckit = integration.get("speckit") or {}
    if not isinstance(speckit, MutableMapping):
        return

    if not bool(cfg.get("markTaskCheckbox", True)):
        return

    tasks_md_rel = str(speckit.get("tasks_md") or "").strip()
    task_id = str(speckit.get("task_id") or "").strip()
    if not tasks_md_rel or not task_id:
        return

    tasks_md_path = project_root / tasks_md_rel
    if not tasks_md_path.exists():
        _record_sync(ctx, "speckit", ok=False, detail=f"tasks_md_missing:{tasks_md_rel}")
        return

    try:
        original = tasks_md_path.read_text(encoding="utf-8")
    except Exception:
        _record_sync(ctx, "speckit", ok=False, detail=f"tasks_md_unreadable:{tasks_md_rel}")
        return

    updated, changed = _mark_speckit_task_checked(original, task_id=task_id)
    if not changed:
        _record_sync(ctx, "speckit", ok=True, detail=f"no_change:{task_id}")
        return

    try:
        tasks_md_path.write_text(updated, encoding="utf-8")
        _record_sync(ctx, "speckit", ok=True, detail=f"checked:{task_id}")
    except Exception:
        _record_sync(ctx, "speckit", ok=False, detail=f"tasks_md_unwritable:{tasks_md_rel}")


def _sync_openspec_impl(
    ctx: MutableMapping[str, Any],
    integration: MutableMapping[str, Any],
    *,
    project_root: Path,
    cfg: MutableMapping[str, Any],
) -> None:
    openspec = integration.get("openspec") or {}
    if not isinstance(openspec, MutableMapping):
        return

    if not bool(cfg.get("markAllCheckboxes", True)):
        return

    tasks_md_rel = str(openspec.get("tasks_md") or "").strip()
    if not tasks_md_rel:
        return

    tasks_md_path = project_root / tasks_md_rel
    if not tasks_md_path.exists():
        _record_sync(ctx, "openspec", ok=False, detail=f"tasks_md_missing:{tasks_md_rel}")
        return

    try:
        original = tasks_md_path.read_text(encoding="utf-8")
    except Exception:
        _record_sync(ctx, "openspec", ok=False, detail=f"tasks_md_unreadable:{tasks_md_rel}")
        return

    updated, changed = _mark_all_checkboxes_checked(original)
    if not changed:
        _record_sync(ctx, "openspec", ok=True, detail="no_change")
        return

    try:
        tasks_md_path.write_text(updated, encoding="utf-8")
        _record_sync(ctx, "openspec", ok=True, detail="checked_all")
    except Exception:
        _record_sync(ctx, "openspec", ok=False, detail=f"tasks_md_unwritable:{tasks_md_rel}")


def _mark_speckit_task_checked(content: str, *, task_id: str) -> tuple[str, bool]:
    changed = False
    lines: list[str] = []
    for line in content.splitlines(keepends=False):
        m = _SPECKIT_TASK_LINE.match(line)
        if m and m.group(4) == task_id:
            if m.group(2).lower() != "x":
                line = f"{m.group(1)}x{m.group(3)}{m.group(4)}{m.group(5)}"
                changed = True
        lines.append(line)
    return "\n".join(lines) + ("\n" if content.endswith("\n") else ""), changed


def _mark_all_checkboxes_checked(content: str) -> tuple[str, bool]:
    changed = False
    lines: list[str] = []
    for line in content.splitlines(keepends=False):
        m = _CHECKBOX_LINE.match(line)
        if m:
            if m.group(2).lower() != "x":
                line = f"{m.group(1)}x{m.group(3)}{m.group(4)}"
                changed = True
        lines.append(line)
    return "\n".join(lines) + ("\n" if content.endswith("\n") else ""), changed


def _get_external_sync_config(project_root: Path) -> dict[str, Any]:
    try:
        from edison.core.config.cache import get_cached_config

        cfg = get_cached_config(project_root)
        tasks_cfg = cfg.get("tasks", {}) if isinstance(cfg, dict) else {}
        integrations = tasks_cfg.get("integrations", {}) if isinstance(tasks_cfg, dict) else {}
        external = (
            integrations.get("externalSync", {})
            if isinstance(integrations, dict)
            else {}
        )
        return external if isinstance(external, dict) else {}
    except Exception:
        return {}


def _record_sync(ctx: MutableMapping[str, Any], kind: str, *, ok: bool, detail: str) -> None:
    ctx.setdefault("_actions", []).append(f"sync_external_task_sources:{kind}:{'ok' if ok else 'err'}:{detail}")
