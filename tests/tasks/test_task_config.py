"""Task configuration must be YAML-driven with no hardcoded defaults.

This test asserts that task roots and state machine values are loaded from
configuration files placed under ``.edison/core/config`` for an isolated
project. The new ``TaskConfig`` helper should respect the repo root passed
by the caller and avoid hardcoded paths or states.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


@pytest.mark.task
def test_task_config_reads_paths_and_states(tmp_path: Path, monkeypatch):
    """TaskConfig must resolve all paths and states from YAML config."""
    repo = tmp_path
    (repo / ".git").mkdir()

    # Core config placed under .edison/core/config inside the temp repo
    config_dir = repo / ".edison" / "core" / "config"
    _write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "task": {
                    "states": {
                        "backlog": {"allowed_transitions": [{"to": "doing"}]},
                        "doing": {"allowed_transitions": [{"to": "review"}, {"to": "backlog"}]},
                        "review": {"allowed_transitions": [{"to": "done"}, {"to": "doing"}]},
                        "done": {"allowed_transitions": []},
                    },
                },
                "qa": {
                    "states": {
                        "waiting": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "approved"}]},
                        "approved": {"allowed_transitions": []},
                    },
                },
            }
        },
    )

    _write_yaml(
        config_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/custom-tasks",
                    "qaRoot": ".project/custom-qa",
                    "metaRoot": ".project/custom-meta",
                }
            }
        },
    )

    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None

    from edison.core.task.config import TaskConfig 
    cfg = TaskConfig(repo_root=repo)

    assert cfg.tasks_root() == (repo / ".project/custom-tasks").resolve()
    assert cfg.qa_root() == (repo / ".project/custom-qa").resolve()
    assert cfg.meta_root() == (repo / ".project/custom-meta").resolve()
    assert set(cfg.task_states()) == {"backlog", "doing", "review", "done"}
    assert cfg.transitions("task") == {
        "backlog": ["doing"],
        "doing": ["review", "backlog"],
        "review": ["done", "doing"],
        "done": [],
    }
