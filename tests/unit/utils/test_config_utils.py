"""Tests for centralized config utilities.

Following strict TDD: These tests are written FIRST (RED phase).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from helpers.io_utils import write_yaml


def _write_test_config(repo_root: Path) -> None:
    """Write test config files to isolated project."""
    # State machine config
    state_machine = {
        "statemachine": {
            "task": {
                "states": {
                    "todo": {"description": "Task awaiting claim", "initial": True},
                    "wip": {"description": "Task in progress"},
                    "done": {"description": "Implementation complete"},
                    "validated": {"description": "Validated and complete", "final": True},
                }
            },
            "qa": {
                "states": {
                    "waiting": {"description": "Pending hand-off", "initial": True},
                    "todo": {"description": "QA backlog"},
                    "wip": {"description": "QA in progress"},
                    "done": {"description": "QA review complete"},
                    "validated": {"description": "QA validated", "final": True},
                }
            },
        }
    }

    # Workflow config with lifecycle (top-level keys, no wrapper)
    workflow = {
        "validationLifecycle": {
            "onApprove": {
                "taskState": "done → validated",
                "qaState": "done → validated",
            },
            "onReject": {
                "taskState": "done → wip",
                "qaState": "done → waiting",
            },
            "onRevalidate": {
                "qaState": "validated → todo",
            },
        },
        "timeouts": {
            "session": "2h",
            "validation": "30m",
        },
    }

    cfg_dir = repo_root / ".edison" / "config"
    write_yaml(cfg_dir / "state-machine.yaml", state_machine)
    write_yaml(cfg_dir / "workflow.yaml", workflow)


@pytest.fixture()
def config_utils(isolated_project_env: Path):
    """Load config utils module with test config."""
    _write_test_config(isolated_project_env)

    # Clear config caches to ensure test config is loaded
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Clear lru_cache on our utility functions
    from edison.core.utils import config
    config._load_config_section_impl.cache_clear()

    # Import WorkflowConfig class for state functions
    from edison.core.config.domains.workflow import WorkflowConfig

    # Return utils module and WorkflowConfig instance
    return {"utils": config, "workflow": WorkflowConfig(repo_root=isolated_project_env)}


def test_load_config_section_returns_section(config_utils):
    """load_config_section returns requested section from YAML."""
    section = config_utils["utils"].load_config_section("statemachine")

    assert isinstance(section, dict)
    assert "task" in section
    assert "qa" in section
    assert "todo" in section["task"]["states"]
    assert "waiting" in section["qa"]["states"]


def test_load_config_section_validation_lifecycle(config_utils):
    """load_config_section can load validationLifecycle section."""
    # validationLifecycle is a top-level key in the merged config
    section = config_utils["utils"].load_config_section("validationLifecycle")

    assert isinstance(section, dict)
    assert "onApprove" in section
    assert "onReject" in section


def test_load_config_section_missing_raises(config_utils):
    """load_config_section raises on missing required section."""
    with pytest.raises(KeyError, match="nonexistent"):
        config_utils["utils"].load_config_section("nonexistent", required=True)


def test_load_config_section_missing_returns_empty_when_optional(config_utils):
    """load_config_section returns empty dict for missing optional section."""
    section = config_utils["utils"].load_config_section("nonexistent", required=False)
    assert section == {}


def test_get_states_for_domain_task(config_utils):
    """get_states('task') returns task states from config."""
    states = config_utils["workflow"].get_states("task")

    assert isinstance(states, list)
    assert "todo" in states
    assert "wip" in states
    assert "done" in states
    assert "validated" in states


def test_get_states_for_domain_qa(config_utils):
    """get_states('qa') returns qa states from config."""
    states = config_utils["workflow"].get_states("qa")

    assert isinstance(states, list)
    assert "waiting" in states
    assert "todo" in states
    assert "wip" in states
    assert "done" in states
    assert "validated" in states


def test_get_initial_state_returns_config_value(config_utils):
    """get_initial_state uses semantic state mapping."""
    # Task initial should be 'todo' (first state marked initial)
    task_initial = config_utils["workflow"].get_initial_state("task")
    assert task_initial == "todo"

    # QA initial should be 'waiting'
    qa_initial = config_utils["workflow"].get_initial_state("qa")
    assert qa_initial == "waiting"


def test_get_final_state_task(config_utils):
    """get_final_state returns 'validated' for task domain."""
    state = config_utils["workflow"].get_final_state("task")
    assert state == "validated"


def test_get_final_state_qa(config_utils):
    """get_final_state returns 'validated' for qa domain."""
    state = config_utils["workflow"].get_final_state("qa")
    assert state == "validated"


def test_get_semantic_state_task_validated(config_utils):
    """get_semantic_state resolves 'validated' from lifecycle."""
    # Should parse target from "done → validated"
    state = config_utils["workflow"].get_semantic_state("task", "validated")
    assert state == "validated"


def test_get_semantic_state_qa_waiting(config_utils):
    """get_semantic_state resolves 'waiting' from lifecycle."""
    # Should parse target from rejection transition (done → waiting in test config)
    state = config_utils["workflow"].get_semantic_state("qa", "waiting")
    assert state == "waiting"


def test_get_semantic_state_unknown_returns_key(config_utils):
    """get_semantic_state returns the key itself if not mapped."""
    state = config_utils["workflow"].get_semantic_state("task", "unknown_state")
    assert state == "unknown_state"


def test_load_config_section_with_explicit_repo_root(isolated_project_env: Path):
    """load_config_section accepts explicit repo_root parameter."""
    _write_test_config(isolated_project_env)
    
    # Clear caches to ensure test config is loaded
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()
    
    from edison.core.utils import config
    config._load_config_section_impl.cache_clear()

    section = config.load_config_section(
        "statemachine",
        repo_root=isolated_project_env
    )
    assert isinstance(section, dict)
    assert "task" in section


def test_get_states_caches_result(config_utils):
    """get_states returns consistent results (cached)."""
    states1 = config_utils["workflow"].get_states("task")
    states2 = config_utils["workflow"].get_states("task")

    # Should return same list
    assert states1 == states2
    assert states1 is states2  # Same object (cached)
