"""Session state management driven by rich declarative config."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from ..exceptions import SessionStateError
from ..state import (
    RichStateMachine,
    StateTransitionError,
    action_registry,
    condition_registry,
    guard_registry,
)
from ._config import get_config as _get_session_config


_STATE_MACHINE: Optional[RichStateMachine] = None


def _get_config():
    """Get SessionConfig using centralized accessor."""
    return _get_session_config()


def _machine() -> RichStateMachine:
    global _STATE_MACHINE
    if _STATE_MACHINE is None:
        config = _get_config()
        spec = (config._state_config or {}).get("session", {})  # type: ignore[attr-defined]
        _STATE_MACHINE = RichStateMachine(
            "session",
            spec,
            guard_registry,
            condition_registry,
            action_registry,
        )
    return _STATE_MACHINE


def _build_context(context: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    base = dict(context or {})
    base.setdefault("config", {})
    return base


def validate_transition(from_state: str, to_state: str, *, context: Optional[Mapping[str, Any]] = None) -> bool:
    """Validate if a transition from from_state to to_state is allowed."""
    try:
        machine = _machine()
        machine.validate(from_state, to_state, context=_build_context(context))
        return True
    except StateTransitionError as exc:
        raise SessionStateError(
            str(exc),
            context={"from": from_state, "to": to_state, **getattr(exc, "context", {})},
        ) from exc


def get_initial_state() -> str:
    """Return the initial state for a new session."""
    return _get_config().get_initial_state("session")


def is_final_state(state: str) -> bool:
    """Check if a state is final."""
    return _get_config().is_final_state("session", state)


def build_default_state_machine() -> RichStateMachine:
    """Expose the session state machine for tests."""
    return _machine()
