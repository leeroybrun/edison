"""Config-backed state transition validator.

Provides a single entry point to validate transitions for session/task/qa
using the declarative state machine defined in YAML. No implicit defaults
or allow-all behavior: if the spec is missing, validation fails fast.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Optional

from edison.core.config.cache import get_cached_config
from edison.core.state import RichStateMachine, StateTransitionError
from edison.core.state import guard_registry, condition_registry, action_registry


class MissingStateMachine(ValueError):
    """Raised when a requested entity has no state machine configured."""


class StateValidator:
    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else None

    @lru_cache(maxsize=16)
    def _machine(self, entity: str) -> RichStateMachine:
        cfg = get_cached_config(repo_root=self.repo_root)
        sm_spec = cfg.get("statemachine", {}) or {}
        entity_spec = sm_spec.get(entity)
        if not isinstance(entity_spec, Mapping):
            raise MissingStateMachine(f"State machine not configured for entity '{entity}'")
        return RichStateMachine(
            entity,
            {"states": entity_spec.get("states", {})},
            guard_registry,
            condition_registry,
            action_registry,
        )

    def ensure_transition(
        self,
        entity: str,
        current: str,
        target: str,
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> None:
        machine = self._machine(entity)
        machine.validate(current, target, context=context or {}, execute_actions=False)


__all__ = ["StateValidator", "MissingStateMachine"]

