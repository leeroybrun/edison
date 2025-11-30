import pytest
import yaml
from edison.core.state.validator import StateValidator
from edison.core.config.domains.session import SessionConfig
from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches
from edison.core.state import StateTransitionError
from edison.core.state.guards import registry as guard_registry
from edison.core.state.conditions import registry as condition_registry
from edison.core.state.actions import registry as action_registry
import edison.core.utils.paths.resolver as path_resolver

@pytest.fixture
def session_config(tmp_path, monkeypatch):
    """
    Sets up a temporary config for state transitions.
    """
    # Reset ALL caches first
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)
    
    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))
    
    # Define a rich state machine with guards/conditions/actions
    state_machine = {
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
                                "to": "validated",
                                "conditions": [
                                    {"name": "ready_to_close", "error": "session not ready"}
                                ],
                                "actions": [{"name": "record_closed"}],
                            }
                        ],
                    },
                    "validated": {"final": True, "allowed_transitions": []},
                },
            }
        }
    }
    (config_dir / "state-machine.yml").write_text(yaml.dump(state_machine))
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    
    # Reset global registries used by state module
    guard_registry.reset()
    condition_registry.reset()
    action_registry.reset()
    guard_registry.register("always_allow", lambda ctx: True)
    condition_registry.register("ready_to_close", lambda ctx: ctx.get("session", {}).get("ready", False))
    action_registry.register("record_closed", lambda ctx: ctx.setdefault("log", []).append("closed"))

    # Reset caches AFTER env vars are set
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    yield tmp_path

    # Cleanup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

def test_validate_transition(session_config):
    """Test validating state transitions."""
    validator = StateValidator(repo_root=session_config)

    # Valid transitions - ensure_transition doesn't raise
    validator.ensure_transition("session", "active", "closing")
    validator.ensure_transition("session", "closing", "validated", context={"session": {"ready": True}})
    validator.ensure_transition("session", "active", "active")

    # Invalid transitions
    with pytest.raises(StateTransitionError):
        validator.ensure_transition("session", "active", "validated")  # Skip closing

    with pytest.raises(StateTransitionError):
        validator.ensure_transition("session", "validated", "active")  # Backwards

def test_get_initial_state(session_config):
    """Test getting the initial state."""
    config = SessionConfig(repo_root=session_config)
    assert config.get_initial_state("session") == "active"

def test_is_final_state(session_config):
    """Test checking final state."""
    config = SessionConfig(repo_root=session_config)
    assert config.is_final_state("session", "validated") is True
    assert config.is_final_state("session", "active") is False


def test_condition_failure_blocks_transition(session_config):
    """Closing requires condition to be true."""
    validator = StateValidator(repo_root=session_config)
    with pytest.raises(StateTransitionError):
        validator.ensure_transition("session", "closing", "validated", context={"session": {"ready": False}})
