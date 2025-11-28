"""Record path resolution with config-driven roots.

This module centralizes derivation of on-disk locations for sessions,
tasks, QA records, and validation evidence using ONLY YAML configuration
values. It avoids domain-specific rules beyond translating configured
state → directory mappings and keeps logic minimal to prevent "god" utils.

Domain-specific helpers should live alongside their domains; this module
exposes only shared, config-driven path composition.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from edison.core.config.domains import SessionConfig, TaskConfig
from edison.core.utils.paths import PathResolver


class RecordPaths:
    """Config-driven paths for session, task, qa, and evidence artifacts."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = PathResolver.resolve_project_root() if repo_root is None else Path(repo_root).resolve()
        self.session_cfg = SessionConfig(repo_root=self.repo_root)
        self.task_cfg = TaskConfig(repo_root=self.repo_root)

    # ---------------- Session paths -----------------
    def sessions_root(self) -> Path:
        return (self.repo_root / self.session_cfg.get_session_root_path()).resolve()

    def session_state_dir(self, state: str) -> Path:
        states = self.session_cfg.get_session_states()
        dirname = states.get(state)
        if dirname is None:
            raise KeyError(f"Unknown session state '{state}'")
        return (self.sessions_root() / dirname).resolve()

    def session_json_path(self, session_id: str, state: Optional[str] = None) -> Path:
        target_state = state or self.session_cfg.get_initial_session_state()
        return self.session_state_dir(target_state) / session_id / "session.json"

    # ---------------- Task paths -----------------
    def tasks_root(self) -> Path:
        return self.task_cfg.tasks_root()

    def task_state_dir(self, state: str) -> Path:
        return (self.tasks_root() / state).resolve()

    # ---------------- QA paths -----------------
    def qa_root(self) -> Path:
        return self.task_cfg.qa_root()

    def qa_state_dir(self, state: str) -> Path:
        return (self.qa_root() / state).resolve()

    # ---------------- Evidence paths -----------------
    def evidence_root(self, task_id: str) -> Path:
        return (self.qa_root() / "validation-evidence" / task_id).resolve()


__all__ = ["RecordPaths"]

