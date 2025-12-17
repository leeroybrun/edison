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
        """Get the state machine configuration.

        Canonical source of truth is `workflow.statemachine` (WorkflowConfig),
        not a top-level `statemachine` section.
        """
        from edison.core.config.domains.workflow import WorkflowConfig

        wf = WorkflowConfig(repo_root=self.repo_root)
        return dict(wf._statemachine)

    # --- State Machine ---
    def get_states(self, entity: str) -> List[str]:
        """Get list of valid states for an entity (e.g., 'task', 'qa', 'session')."""
        from edison.core.config.domains.workflow import WorkflowConfig

        return WorkflowConfig(repo_root=self.repo_root).get_states(entity)

    def get_transitions(self, entity: str) -> Dict[str, List[str]]:
        """Get transition map for an entity."""
        from edison.core.config.domains.workflow import WorkflowConfig

        return WorkflowConfig(repo_root=self.repo_root).get_transitions(entity)

    def validate_transition(self, entity: str, current_state: str, next_state: str) -> bool:
        """Check if a transition is valid."""
        if current_state == next_state:
            return True
        transitions = self.get_transitions(entity)
        allowed = transitions.get(current_state, [])
        return next_state in allowed

    def get_initial_state(self, entity: str) -> str:
        """Return the initial state for an entity (default: active)."""
        from edison.core.config.domains.workflow import WorkflowConfig

        try:
            return WorkflowConfig(repo_root=self.repo_root).get_initial_state(entity)
        except Exception:
            return "active"

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
        """Get relative path to sessions root (must be configured in YAML)."""
        path = self.section.get("paths", {}).get("root")
        if not path:
            raise ValueError("session.paths.root not configured")
        return str(path)

    def get_archive_root_path(self) -> str:
        """Get relative path to archive root (must be configured in YAML)."""
        path = self.section.get("paths", {}).get("archive")
        if not path:
            raise ValueError("session.paths.archive not configured")
        return str(path)

    def get_tx_root_path(self) -> str:
        """Get relative path to transaction root (must be configured in YAML)."""
        path = self.section.get("paths", {}).get("tx")
        if not path:
            raise ValueError("session.paths.tx not configured")
        return str(path)

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
        """Get mapping of session states to directory names (no defaults)."""
        states = self.section.get("states") if isinstance(self.section, dict) else None
        if not isinstance(states, dict) or not states:
            raise ValueError("session.states not configured")
        return {str(k): str(v) for k, v in states.items()}

    def get_initial_session_state(self) -> str:
        """Get the default initial state for a new session."""
        # 1) explicit session defaults
        defaults = self.section.get("defaults", {})
        if isinstance(defaults, dict) and defaults.get("initialState"):
            return str(defaults["initialState"])
        # 2) statemachine session state marker (canonical: workflow.statemachine)
        try:
            from edison.core.config.domains.workflow import WorkflowConfig

            return WorkflowConfig(repo_root=self.repo_root).get_initial_state("session")
        except Exception:
            pass
        # 3) first configured session state if present
        sess_states = self.get_session_states()
        if sess_states:
            return next(iter(sess_states.keys()))
        raise ValueError("session.initialState not configured")

    def get_session_lookup_order(self) -> List[str]:
        """Get the order of states to check when looking up a session."""
        order = self.section.get("lookupOrder")
        if isinstance(order, list) and order:
            return [str(s) for s in order]
        states = self.get_session_states()
        if states:
            return list(states.keys())
        raise ValueError("session.lookupOrder not configured and no states available")

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
            "baseBranchMode": "current",
            "baseBranch": None,
            "branchPrefix": "session/",
            "baseDirectory": ".worktrees",
            "archiveDirectory": ".worktrees/_archived",
            "pathTemplate": "../{PROJECT_NAME}-worktrees/{sessionId}",
            "cleanup": {
                "autoArchive": True,
                "archiveAfterDays": 30,
                "deleteAfterDays": 90,
            },
            "enforcement": {
                # When enabled, certain session-scoped commands are blocked unless the
                # current working directory is inside the session worktree.
                #
                # This is intentionally opt-in because some workflows use the primary
                # checkout for discovery (task listing, session creation) before
                # switching into the worktree.
                "enabled": True,
                "commands": [
                    "session close",
                    "session next",
                    "session status",
                    "session track",
                    "session verify",
                    "session complete",
                    "session validate",
                    "task claim",
                    "task status",
                    "task mark-delegated",
                    "task split",
                    "task link",
                    "qa validate",
                    "qa run",
                    "qa bundle",
                    "qa promote",
                ],
            },
            # Optional worktree features (kept here for backward compatibility with
            # existing project overlays; schema allows these keys).
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

    def get_worktree_uuid_suffix_length(self) -> int:
        """Get UUID suffix length for worktree naming collisions."""
        val = self.section.get("worktree", {}).get("uuidSuffixLength")
        if val is None:
            raise ValueError("session.worktree.uuidSuffixLength not configured")
        return int(val)

    # --- Database Config ---
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self._config.get("database", {})

    # --- Recovery Config ---
    def get_recovery_config(self) -> Dict[str, Any]:
        """Get recovery configuration (timeouts, etc)."""
        return self.section.get("recovery", {})

    def get_recovery_default_timeout_minutes(self) -> int:
        """Get default timeout in minutes for recovery operations."""
        rec_cfg = self.get_recovery_config()
        val = rec_cfg.get("defaultTimeoutMinutes")
        if val is None:
            raise ValueError("session.recovery.defaultTimeoutMinutes not configured")
        return int(val)

    # --- Transaction Config ---
    def get_transaction_min_disk_headroom(self) -> int:
        """Get minimum disk headroom in bytes for transaction operations."""
        val = self.section.get("transaction", {}).get("minDiskHeadroom")
        if val is None:
            raise ValueError("session.transaction.minDiskHeadroom not configured")
        return int(val)


__all__ = ["SessionConfig"]
