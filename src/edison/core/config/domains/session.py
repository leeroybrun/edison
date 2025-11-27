"""Domain-specific configuration for sessions.

Provides cached access to session configuration including state machine,
paths, validation, worktrees, and database settings.
"""
from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseDomainConfig

logger = logging.getLogger(__name__)


class SessionConfig(BaseDomainConfig):
    """Provides access to session configuration (states, paths, validation).

    Loads from bundled defaults (edison.data) with project overrides (.edison/config/).
    Extends BaseDomainConfig for consistent caching and repo_root handling.

    Note: This config accesses multiple sections (session, statemachine, worktrees)
    as they are tightly coupled for session management.
    """

    def _config_section(self) -> str:
        return "session"

    @cached_property
    def _state_config(self) -> Dict[str, Any]:
        """Get the statemachine configuration section."""
        return self._config.get("statemachine", {}) or {}

    # --- State Machine ---
    def get_states(self, entity: str) -> List[str]:
        """Get list of valid states for an entity (e.g., 'task', 'qa')."""
        entity_config = self._state_config.get(entity, {})
        states = entity_config.get("states", {})
        if isinstance(states, dict):
            return list(states.keys())
        return list(states or [])

    def get_transitions(self, entity: str) -> Dict[str, List[str]]:
        """Get transition map for an entity."""
        from edison.core.state import _flatten_transitions

        entity_config = self._state_config.get(entity, {})
        states = entity_config.get("states", {})
        if isinstance(states, dict):
            return _flatten_transitions(states)
        return entity_config.get("transitions", {})

    def validate_transition(self, entity: str, current_state: str, next_state: str) -> bool:
        """Check if a transition is valid."""
        if current_state == next_state:
            return True
        transitions = self.get_transitions(entity)
        allowed = transitions.get(current_state, [])
        return next_state in allowed

    def get_initial_state(self, entity: str) -> str:
        """Return the initial state for an entity (default: active)."""
        entity_config = self._state_config.get(entity, {})
        states = entity_config.get("states", {})
        if isinstance(states, list):
            # Simple list of strings
            return states[0] if states else "active"
        elif isinstance(states, dict):
            # Rich object format
            for name, info in states.items():
                if isinstance(info, dict) and info.get("initial"):
                    return name
        return "active"  # Default initial state if not specified

    def is_final_state(self, entity: str, state: str) -> bool:
        """Check if a state is final for an entity."""
        entity_config = self._state_config.get(entity, {})
        states = entity_config.get("states", {})
        if isinstance(states, list):
            transitions = self.get_transitions(entity)
            return not bool(transitions.get(state))
        elif isinstance(states, dict):
            info = states.get(state)
            if info:
                return info.get("final", False)
        return False

    # --- Session Paths & Validation ---
    def get_session_root_path(self) -> str:
        """Get relative path to sessions root (e.g. '.project/sessions')."""
        return self.section.get("paths", {}).get("root", ".project/sessions")

    def get_archive_root_path(self) -> str:
        """Get relative path to archive root (e.g. '.project/archive')."""
        return self.section.get("paths", {}).get("archive", ".project/archive")

    def get_tx_root_path(self) -> str:
        """Get relative path to transaction root (e.g. '.project/sessions/_tx')."""
        return self.section.get("paths", {}).get("tx", ".project/sessions/_tx")

    def get_template_path(self, key: str) -> str:
        """Get expanded path to a template (e.g. 'primary', 'repo')."""
        from edison.core.utils.paths import PathResolver
        from edison.core.utils.paths import get_project_config_dir

        root = PathResolver.resolve_project_root()
        project_dir = get_project_config_dir(root)
        raw = self.section.get("paths", {}).get("templates", {}).get(key, "")

        if raw:
            return str(self._expand_path(raw, root=root, project_dir=project_dir))

        # Fallback: default to project config sessions template
        return str((project_dir / "sessions" / "TEMPLATE.json").resolve())

    def _expand_path(self, raw: str, *, root: Path, project_dir: Path) -> Path:
        """Expand template tokens in session path strings."""
        tokens: Dict[str, str] = {
            "PROJECT_ROOT": str(root),
            "PROJECT_DIR": str(project_dir),
            "PROJECT_CONFIG_DIR": str(project_dir),
            "PROJECT_CONFIG_BASENAME": project_dir.name,
        }

        try:
            expanded = raw.format(**tokens)
        except Exception:
            expanded = raw

        path = Path(expanded)
        if not path.is_absolute():
            path = (root / path).resolve()
        return path

    def get_id_regex(self) -> str:
        """Get regex for session ID validation."""
        return self.section.get("validation", {}).get("idRegex", r"^[a-zA-Z0-9_\-\.]+$")

    def get_max_id_length(self) -> int:
        """Get max length for session ID."""
        val = self.section.get("validation", {}).get("maxLength")
        if val is None:
            raise ValueError("session.validation.maxLength not configured")
        return int(val)

    def get_session_states(self) -> Dict[str, str]:
        """Get mapping of session states to directory names."""
        return self.section.get(
            "states",
            {
                "draft": "draft",
                "active": "wip",
                "wip": "wip",
                "done": "done",
                "closing": "done",
                "validated": "validated",
                "recovery": "recovery",
                "archived": "archived",
            },
        )

    def get_initial_session_state(self) -> str:
        """Get the default initial state for a new session."""
        # 1) explicit session defaults
        defaults = self.section.get("defaults", {})
        if isinstance(defaults, dict) and defaults.get("initialState"):
            return str(defaults["initialState"])
        # 2) statemachine session state marker
        sm_session = self._state_config.get("session", {})
        sm_states = sm_session.get("states", {})
        if isinstance(sm_states, dict):
            for name, info in sm_states.items():
                if isinstance(info, dict) and info.get("initial"):
                    return str(name)
        # 3) first configured session state if present
        sess_states = self.get_session_states()
        if isinstance(sess_states, dict) and sess_states:
            return next(iter(sess_states.keys()))
        # 4) sane default
        return "active"

    def get_session_lookup_order(self) -> List[str]:
        """Get the order of states to check when looking up a session."""
        order = self.section.get("lookupOrder")
        if isinstance(order, list) and order:
            return [str(s) for s in order]
        # Fallback to the explicit states map if order not provided
        states = self.get_session_states()
        if isinstance(states, dict) and states:
            return list(states.keys())
        # Final fallback to sane defaults aligned with YAML
        return ["wip", "active", "done", "validated", "closing", "recovery", "archived", "draft"]

    def get_naming_config(self) -> Dict[str, Any]:
        """Return naming strategy configuration with defaults applied."""
        defaults = {"strategy": "edison", "ensure_unique": True}
        raw = self.section.get("naming", {}) if isinstance(self.section, dict) else {}
        cfg = defaults.copy()
        if isinstance(raw, dict):
            cfg.update(raw)
        return cfg

    # --- Worktree Config ---
    def get_worktree_config(self) -> Dict[str, Any]:
        """Get worktree configuration (merged from defaults and overrides)."""
        from edison.core.utils.paths import get_project_config_dir

        defaults = {
            "enabled": True,
            "baseBranch": "main",
            "branchPrefix": "session/",
            "baseDirectory": ".worktrees",
            "archiveDirectory": ".worktrees/_archived",
            "installDeps": False,
            "enableDatabaseIsolation": False,
            "autoCleanupOnMerge": False,
        }
        cfg = dict(defaults)
        cfg.update(self._config.get("worktrees", {}) or {})
        # Merge overrides from manifest.json when present
        try:
            root = self.repo_root

            # Use central logic to find config dir (respects .edison, env vars, etc)
            manifest_path = get_project_config_dir(root) / "manifest.json"

            if manifest_path.exists():
                from edison.core.utils.io import read_json

                manifest = read_json(manifest_path)
                if isinstance(manifest, dict):
                    wt = manifest.get("worktrees")
                    if isinstance(wt, dict):
                        cfg.update(wt)
        except Exception:
            pass
        return cfg

    def get_worktree_timeout(self, key: str, default: int = 30) -> int:
        """Get timeout for worktree operations."""
        return int(self.section.get("worktree", {}).get("timeouts", {}).get(key, default))

    # --- Database Config ---
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self._config.get("database", {})

    # --- Recovery Config ---
    def get_recovery_config(self) -> Dict[str, Any]:
        """Get recovery configuration (timeouts, etc)."""
        return self.section.get("recovery", {})


__all__ = ["SessionConfig"]



