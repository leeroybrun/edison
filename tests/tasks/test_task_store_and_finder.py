"""Integration smoke tests for the new ``lib.task`` namespace.

These tests exercise the store and finder helpers end-to-end using an
isolated repository rooted at ``tmp_path``. They ensure configuration-driven
paths are respected and that task discovery works without the legacy
``task`` module.
"""
from __future__ import annotations

from pathlib import Path

import importlib
import yaml


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _bootstrap_repo(repo: Path) -> None:
    (repo / ".git").mkdir()
    config_dir = repo / ".edison" / "core" / "config"
    _write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}, {"to": "todo"}]},
                        "done": {"allowed_transitions": []},
                    },
                },
                "qa": {
                    "states": {
                        "waiting": {"allowed_transitions": [{"to": "todo"}]},
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}, {"to": "todo"}]},
                        "done": {"allowed_transitions": []},
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
                    "root": ".project/tasks",
                    "qaRoot": ".project/qa",
                    "metaRoot": ".project/tasks/meta",
                    "template": ".project/tasks/TEMPLATE.md",
                },
                "defaults": {
                    "ownerPrefix": "- **Owner:** ",
                    "validatorOwnerPrefix": "- **Validator Owner:** ",
                    "statusPrefix": "- **Status:** ",
                    "claimedPrefix": "  - **Claimed At:** ",
                    "lastActivePrefix": "  - **Last Active:** ",
                    "continuationPrefix": "  - **Continuation ID:** ",
                },
            }
        },
    )


def test_create_and_find_task(tmp_path, monkeypatch):
    repo = tmp_path
    _bootstrap_repo(repo)

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver

    resolver._PROJECT_ROOT_CACHE = None

    import edison.core.task.paths as paths
    paths = importlib.reload(paths)

    # Reload metadata-dependent modules so TYPE_INFO picks up new roots
    import edison.core.task.record_metadata as metadata
    metadata = importlib.reload(metadata)
    importlib.reload(importlib.import_module("edison.core.task.io"))
    importlib.reload(importlib.import_module("edison.core.task.store"))
    importlib.reload(importlib.import_module("edison.core.task.finder"))

    for d in [*paths.TASK_DIRS.values(), *paths.QA_DIRS.values(), *paths.SESSION_DIRS.values()]:
        d.mkdir(parents=True, exist_ok=True)

    from edison.core.task import store, finder

    # Create a task and ensure it lands in the configured todo queue
    path = store.create_task("T-123", "Decompose god module", "desc")
    assert path.exists()
    assert path.parent == paths.TASK_DIRS.get("todo")

    # Finder should locate the task using the new namespace
    found = finder.find_record("T-123", "task")
    assert found == path

    meta = finder.list_records("task")
    ids = {m.record_id for m in meta}
    assert "T-123" in ids
