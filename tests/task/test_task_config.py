"""Task configuration must be YAML-driven with no hardcoded defaults.

This test asserts that task paths are loaded from project configuration files
and that TaskConfig correctly accesses both paths and state machine values.
ConfigManager merges project configs with bundled defaults (edison.data).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from helpers.io_utils import write_yaml


@pytest.mark.task
def test_task_config_reads_paths_from_project_config(tmp_path: Path, monkeypatch):
    """TaskConfig must resolve paths from project config overrides."""
    repo = tmp_path
    (repo / ".git").mkdir()

    # Project config placed under .edison/config/ for ConfigManager
    config_dir = repo / ".edison" / "config"
    write_yaml(
        config_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/custom-tasks",
                    "qaRoot": ".project/custom-qa",
                    "metaRoot": ".project/custom-meta",
                }
            },
        },
    )

    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None

    # Clear config cache to ensure fresh load from test files
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    from edison.core.config.domains import TaskConfig
    cfg = TaskConfig(repo_root=repo)

    # Verify paths come from project config
    assert cfg.tasks_root() == (repo / ".project/custom-tasks").resolve()
    assert cfg.qa_root() == (repo / ".project/custom-qa").resolve()
    assert cfg.meta_root() == (repo / ".project/custom-meta").resolve()

    # Verify state machine loaded from bundled defaults
    # (ConfigManager merges project configs with edison.data/config/)
    task_states = cfg.task_states()
    assert len(task_states) > 0, "Task states should be loaded from bundled defaults"
    # Bundled defaults include states like: todo, wip, done, validated, blocked
    assert "todo" in task_states or "done" in task_states, "Expected bundled default states"

    # Verify transitions method works
    transitions = cfg.transitions("task")
    assert isinstance(transitions, dict), "transitions should return a dict"
