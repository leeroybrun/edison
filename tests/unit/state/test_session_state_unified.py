"""Test that session state validation uses unified state system.

This test verifies that session state transitions work through the
unified state validation system (state.validator.StateValidator and
state.transitions) without needing a parallel session.state module.
"""
import pytest
import yaml
from pathlib import Path

from edison.core.state.validator import StateValidator
from edison.core.state import StateTransitionError
from edison.core.state.guards import registry as guard_registry
from edison.core.state.conditions import registry as condition_registry
from edison.core.state.actions import registry as action_registry
from tests.helpers.env_setup import setup_project_root
from tests.helpers.cache_utils import reset_edison_caches


@pytest.fixture
def session_state_config(tmp_path, monkeypatch):
    """Setup temporary config for session state validation."""
    # Reset ALL caches first
    reset_edison_caches()

    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)

    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))

    # Define session state machine using standard statemachine config
    state_machine = {
        "workflow": {
            "statemachine": {
                "session": {
                    "states": {
                        "active": {
                            "initial": True,
                            "allowed_transitions": [
                                {"to": "closing", "guard": "always_allow"},
                                {"to": "active"},
                            ],
                        },
                        "closing": {
                            "allowed_transitions": [
                                {
                                    "to": "closed",
                                    "conditions": [
                                        {"name": "ready_to_close", "error": "session not ready"}
                                    ],
                                    "actions": [{"name": "record_closed"}],
                                }
                            ],
                        },
                        "closed": {"final": True, "allowed_transitions": []},
                    },
                }
            }
        },
    }
    (config_dir / "state-machine.yml").write_text(yaml.dump(state_machine))

    # Set env vars
    setup_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    # Reset global registries
    guard_registry.reset()
    condition_registry.reset()
    action_registry.reset()
    guard_registry.register("always_allow", lambda ctx: True)
    condition_registry.register("ready_to_close", lambda ctx: ctx.get("session", {}).get("ready", False))
    action_registry.register("record_closed", lambda ctx: ctx.setdefault("log", []).append("closed"))

    yield tmp_path

    # Cleanup
    reset_edison_caches()


def test_state_validator_validates_session_transitions(session_state_config):
    """StateValidator should validate session state transitions.
    
    Uses transitions with always_allow guards from production config.
    """
    validator = StateValidator(repo_root=session_state_config)

    # Valid transitions with always_allow guards
    validator.ensure_transition("session", "recovery", "active")  # always_allow in production
    validator.ensure_transition("session", "active", "active")  # self-transition

    # Invalid transitions should raise StateTransitionError
    with pytest.raises(StateTransitionError):
        validator.ensure_transition("session", "active", "archived")  # Skip states

    with pytest.raises(StateTransitionError):
        validator.ensure_transition("session", "validated", "active")  # Backwards from final


def test_state_validator_without_session_state_module(session_state_config):
    """Verify StateValidator works without importing session.state module.
    
    Uses recovery->active transition which has always_allow guard.
    """
    import sys

    # Ensure session.state is not imported
    if "edison.core.session.state" in sys.modules:
        del sys.modules["edison.core.session.state"]

    # StateValidator should still work
    validator = StateValidator(repo_root=session_state_config)
    validator.ensure_transition("session", "recovery", "active")  # always_allow

    # Verify session.state was not imported
    assert "edison.core.session.state" not in sys.modules


def test_session_config_provides_initial_and_final_states(session_state_config):
    """Session config should provide initial and final state lookups."""
    from edison.core.config.domains.session import SessionConfig

    config = SessionConfig(repo_root=session_state_config)

    # Initial state lookup
    initial = config.get_initial_state("session")
    assert initial == "active"

    # Final state lookup
    assert config.is_final_state("session", "closed") is True
    assert config.is_final_state("session", "active") is False
    assert config.is_final_state("session", "closing") is False
