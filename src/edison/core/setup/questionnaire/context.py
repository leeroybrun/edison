"""Context and config building for setup questionnaire."""
from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

from edison.core.utils.paths import get_management_paths
from edison.core.utils.paths import DEFAULT_PROJECT_CONFIG_PRIMARY

if TYPE_CHECKING:
    from .base import SetupQuestionnaire


def build_context_with_defaults(
    questionnaire: "SetupQuestionnaire",
    answers: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge provided answers with defaults and detected values."""
    context: Dict[str, Any] = {}
    # Defaults from both modes, respecting conditional questions based on provided answers.
    # Use assume_yes=True so no prompting occurs.
    context.update(questionnaire.run(mode="basic", provided_answers=answers or {}, assume_yes=True))
    context.update(questionnaire.run(mode="advanced", provided_answers=answers or {}, assume_yes=True))
    # Provided answers override defaults
    context.update(answers or {})

    # Ensure detected values are applied when answers left blank
    context.setdefault("project_name", questionnaire.detected.get("project_name"))
    context.setdefault("project_type", questionnaire.detected.get("project_type"))

    # Normalise list fields
    for key in ("tech_stack", "packs", "orchestrators", "validators", "agents", "task_states", "session_states"):
        val = context.get(key)
        if val is None:
            context[key] = []

    # Path defaults
    context.setdefault("project_config_dir", DEFAULT_PROJECT_CONFIG_PRIMARY)
    mgmt_path = get_management_paths(questionnaire.repo_root).get_management_root()
    try:
        mgmt_rel = str(mgmt_path.relative_to(questionnaire.repo_root))
    except Exception:
        mgmt_rel = str(mgmt_path)
    if "project_management_dir" not in (answers or {}):
        context["project_management_dir"] = mgmt_rel

    return context


def build_config_dict(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build a YAML-friendly config dictionary from context."""
    coverage_threshold = context.get("coverage_threshold", 0) or 0
    worktrees_enabled = bool(context.get("enable_worktrees"))
    shared_state_mode = str(context.get("worktrees_shared_state_mode") or "meta").strip().lower()

    worktrees_cfg: Dict[str, Any] = {"enabled": worktrees_enabled}
    if worktrees_enabled:
        ss: Dict[str, Any] = {"mode": shared_state_mode}
        if shared_state_mode == "external":
            ss["externalPath"] = str(context.get("worktrees_external_path") or "").strip()
        worktrees_cfg["sharedState"] = ss
    return {
        "paths": {
            # Canonical key used by config loader bootstrap.
            "project_config_dir": context.get("project_config_dir", DEFAULT_PROJECT_CONFIG_PRIMARY),
        },
        # Management root is resolved by ProjectManagementPaths (supports legacy aliases).
        "project_management_dir": context.get("project_management_dir", ".project"),
        "project": {
            "name": context.get("project_name", ""),
            "type": context.get("project_type", ""),
            "tech_stack": context.get("tech_stack") or [],
        },
        "packs": {
            "active": context.get("packs") or [],
        },
        "database": context.get("database", ""),
        "auth": {"provider": context.get("auth_provider", "")},
        "orchestrators": context.get("orchestrators") or [],
        "agents": {"enabled": context.get("agents") or []},
        "worktrees": worktrees_cfg,
        "workflow": {
            "tasks": {"states": context.get("task_states") or []},
            "sessions": {"states": context.get("session_states") or []},
        },
        "tdd": {
            "enforcement": context.get("tdd_enforcement", "warn"),
            # Backward-compatible: historical location for coverage threshold.
            "coverage_threshold": coverage_threshold,
        },
        # Canonical quality coverage settings (preferred by docs/guidelines).
        "quality": {
            "coverage": {
                "overall": coverage_threshold,
                "changed": 100,
            }
        },
        "ci": {
            "commands": {
                "lint": context.get("ci_lint", ""),
                "test": context.get("ci_test", ""),
                "build": context.get("ci_build", ""),
                "type-check": context.get("ci_type_check", ""),
            }
        },
    }
