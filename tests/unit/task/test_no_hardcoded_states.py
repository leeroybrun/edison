"""Tests verifying that no hardcoded state lists exist in task modules.

This ensures all state information comes from config, not fallback lists.
Following strict TDD: these tests will initially FAIL, then PASS after refactoring.
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest
from helpers.env_setup import setup_project_root


def _find_hardcoded_lists_in_file(file_path: Path) -> list[tuple[int, str]]:
    """Parse a Python file and find hardcoded list literals that look like state lists.

    Returns:
        List of (line_number, literal_content) tuples
    """
    if not file_path.exists():
        return []

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return []

    hardcoded = []

    # State keywords to detect
    state_keywords = {"todo", "wip", "done", "validated", "blocked", "waiting"}

    for node in ast.walk(tree):
        # Look for list literals
        if isinstance(node, ast.List):
            # Check if list contains string constants
            if all(isinstance(elt, ast.Constant) and isinstance(elt.value, str) for elt in node.elts):
                list_values = [elt.value.lower() for elt in node.elts]
                # Check if this looks like a state list
                if any(val in state_keywords for val in list_values):
                    # Get line number and values
                    line_num = node.lineno if hasattr(node, 'lineno') else 0
                    hardcoded.append((line_num, str(list_values)))

    return hardcoded


def test_task_paths_no_hardcoded_states():
    """Verify task/paths.py has no hardcoded state fallbacks."""
    from edison.core import task
    module_path = Path(task.__file__).parent / "paths.py"

    hardcoded = _find_hardcoded_lists_in_file(module_path)

    # Filter for actual state lists (not other lists)
    state_lists = [
        (line, content) for line, content in hardcoded
        if any(state in content.lower() for state in ["todo", "wip", "done", "validated", "blocked", "waiting"])
    ]

    assert len(state_lists) == 0, (
        f"Found {len(state_lists)} hardcoded state list(s) in {module_path}:\n"
        + "\n".join(f"  Line {line}: {content}" for line, content in state_lists)
        + "\n\nStates must come from config, not hardcoded fallbacks."
    )


def test_task_finder_no_hardcoded_states():
    """Verify task/finder.py has no hardcoded state fallbacks."""
    from edison.core import task
    module_path = Path(task.__file__).parent / "finder.py"

    hardcoded = _find_hardcoded_lists_in_file(module_path)

    state_lists = [
        (line, content) for line, content in hardcoded
        if any(state in content.lower() for state in ["todo", "wip", "done", "validated", "blocked", "waiting"])
    ]

    assert len(state_lists) == 0, (
        f"Found {len(state_lists)} hardcoded state list(s) in {module_path}:\n"
        + "\n".join(f"  Line {line}: {content}" for line, content in state_lists)
        + "\n\nStates must come from config, not hardcoded fallbacks."
    )


def test_task_record_metadata_no_hardcoded_states():
    """Verify task/record_metadata.py has no hardcoded state fallbacks."""
    from edison.core import task
    module_path = Path(task.__file__).parent / "record_metadata.py"

    hardcoded = _find_hardcoded_lists_in_file(module_path)

    state_lists = [
        (line, content) for line, content in hardcoded
        if any(state in content.lower() for state in ["todo", "wip", "done", "validated", "blocked", "waiting"])
    ]

    assert len(state_lists) == 0, (
        f"Found {len(state_lists)} hardcoded state list(s) in {module_path}:\n"
        + "\n".join(f"  Line {line}: {content}" for line, content in state_lists)
        + "\n\nStates must come from config, not hardcoded fallbacks."
    )


def test_entity_file_repository_no_hardcoded_states():
    """Verify entity/file_repository.py has no hardcoded state fallbacks."""
    from edison.core import entity
    module_path = Path(entity.__file__).parent / "file_repository.py"

    hardcoded = _find_hardcoded_lists_in_file(module_path)

    state_lists = [
        (line, content) for line, content in hardcoded
        if any(state in content.lower() for state in ["todo", "wip", "done", "validated"])
    ]

    assert len(state_lists) == 0, (
        f"Found {len(state_lists)} hardcoded state list(s) in {module_path}:\n"
        + "\n".join(f"  Line {line}: {content}" for line, content in state_lists)
        + "\n\nStates must come from config, not hardcoded fallbacks."
    )


def test_config_functions_work_without_fallbacks(tmp_path):
    """Verify config functions return states without needing fallbacks.

    This test ensures that the config system always provides states,
    so no fallbacks are needed in the code.
    """
    from edison.core.config.domains.workflow import get_task_states, get_qa_states
    from edison.core.config.cache import clear_all_caches
    import os

    # Set up minimal config
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)

    (config_dir / "defaults.yaml").write_text(
        """
statemachine:
  task:
    states:
      todo:
        allowed_transitions:
          - to: wip
      wip:
        allowed_transitions:
          - to: done
      done:
        allowed_transitions: []
  qa:
    states:
      waiting:
        allowed_transitions:
          - to: todo
      todo:
        allowed_transitions:
          - to: wip
      wip:
        allowed_transitions:
          - to: done
      done:
        allowed_transitions: []
""",
        encoding="utf-8",
    )

    (tmp_path / ".git").mkdir()

    # Set up environment - need monkeypatch fixture
    # Since this test doesn't have monkeypatch, we'll handle env manually
    old_root = os.environ.get("AGENTS_PROJECT_ROOT")
    try:
        os.environ["AGENTS_PROJECT_ROOT"] = str(tmp_path)

        # Clear caches manually
        from edison.core.config.cache import clear_all_caches
        clear_all_caches()

        from edison.core.utils.paths import resolver
        resolver._PROJECT_ROOT_CACHE = None

        # Get states from config
        task_states = get_task_states(repo_root=tmp_path)
        qa_states = get_qa_states(repo_root=tmp_path)

        # Verify they are never empty or None
        assert task_states is not None, "get_task_states() returned None"
        assert len(task_states) > 0, "get_task_states() returned empty list"
        assert "todo" in task_states, "get_task_states() missing 'todo' state"

        assert qa_states is not None, "get_qa_states() returned None"
        assert len(qa_states) > 0, "get_qa_states() returned empty list"
        assert "waiting" in qa_states, "get_qa_states() missing 'waiting' state"

    finally:
        if old_root:
            os.environ["AGENTS_PROJECT_ROOT"] = old_root
        else:
            os.environ.pop("AGENTS_PROJECT_ROOT", None)
        clear_all_caches()
