from __future__ import annotations

import os
from pathlib import Path

import pytest

from edison.core.config.cache import clear_all_caches
from edison.core.state.validator import StateValidator


def _write_config(root: Path, yaml_text: str) -> None:
    cfg = root / ".edison" / "config" / "config.yml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(yaml_text, encoding="utf-8")
    (root / ".project").mkdir(exist_ok=True)


def _use_root(tmp_path: Path) -> None:
    os.environ["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    clear_all_caches()


def test_state_validator_allows_declared_transition(tmp_path: Path) -> None:
    _write_config(
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

    validator.ensure_transition("task", "todo", "done")


def test_state_validator_blocks_undeclared_transition(tmp_path: Path) -> None:
    _write_config(
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

