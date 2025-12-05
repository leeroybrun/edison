from __future__ import annotations
from helpers.io_utils import write_config

import os
from pathlib import Path

import pytest

from edison.core.config.cache import clear_all_caches
from edison.core.state.validator import StateValidator

def _use_root(tmp_path: Path) -> None:
    os.environ["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    clear_all_caches()

def test_state_validator_allows_declared_transition(tmp_path: Path) -> None:
    """Test state validator allows declared transitions.
    
    Uses wip->todo transition which has always_allow guard in production.
    """
    write_config(
        tmp_path,
        """
        statemachine:
          task:
            states:
              wip:
                allowed_transitions:
                  - to: todo
                    guard: always_allow
              todo:
                allowed_transitions: []
        """,
    )
    _use_root(tmp_path)

    validator = StateValidator(repo_root=tmp_path)

    # Uses production workflow.yaml which has always_allow for wip->todo
    validator.ensure_transition("task", "wip", "todo")

def test_state_validator_blocks_undeclared_transition(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        """
        statemachine:
          task:
            states:
              todo:
                allowed_transitions:
                  - to: done
              done:
                allowed_transitions: []
        """,
    )
    _use_root(tmp_path)

    validator = StateValidator(repo_root=tmp_path)

    with pytest.raises(Exception):
        validator.ensure_transition("task", "todo", "wip")

