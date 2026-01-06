"""Session-next reportsMissing should not nag validated tasks for validator reports.

Validated tasks are "done" from a workflow perspective; their QA state may be
stale (e.g., todo) in multi-task/bundle workflows. Session-next should not
surface missing validator reports for tasks already in a final task state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers.io_utils import write_yaml
from tests.helpers.cache_utils import reset_all_and_reload
from tests.helpers.env_setup import setup_project_root
from tests.helpers.fixtures import create_repo_with_git


@pytest.fixture
def repo_env(tmp_path: Path, monkeypatch) -> Path:
    repo = create_repo_with_git(tmp_path)

    # Minimal required project structure
    (repo / ".project" / "tasks" / "validated").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "meta").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "validation-reports").mkdir(parents=True, exist_ok=True)

    (repo / ".project" / "tasks" / "TEMPLATE.md").write_text("# TEMPLATE\n", encoding="utf-8")

    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    write_yaml(
        cfg_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/tasks",
                    "qaRoot": ".project/qa",
                    "metaRoot": ".project/tasks/meta",
                    "template": ".project/tasks/TEMPLATE.md",
                    "evidenceSubdir": "validation-reports",
                }
            }
        },
    )

    write_yaml(
        cfg_dir / "workflow.yaml",
        {
            "version": "1.0",
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"initial": True, "allowed_transitions": []},
                        "wip": {"allowed_transitions": []},
                        "done": {"allowed_transitions": []},
                        "validated": {"final": True, "allowed_transitions": []},
                    }
                },
                "qa": {
                    "states": {
                        "waiting": {"initial": True, "allowed_transitions": []},
                        "todo": {"allowed_transitions": []},
                        "wip": {"allowed_transitions": []},
                        "done": {"allowed_transitions": []},
                        "validated": {"final": True, "allowed_transitions": []},
                    }
                },
            },
        },
    )

    setup_project_root(monkeypatch, repo)
    reset_all_and_reload()
    return repo


def test_build_reports_missing_ignores_validated_tasks(repo_env: Path) -> None:
    from edison.core.session.next.actions import build_reports_missing

    session_id = "s1"
    task_id = "task-validated"

    # Validated task in session (used by TaskRepository.find_by_session)
    task_path = repo_env / ".project" / "tasks" / "validated" / f"{task_id}.md"
    task_path.write_text(
        f"""---
id: "{task_id}"
title: "Validated"
session_id: "{session_id}"
---

# Validated
""",
        encoding="utf-8",
    )

    # QA is still "todo" (active state), but we should not require validator reports
    # for a task already in a final task state.
    qa_path = repo_env / ".project" / "qa" / "todo" / f"{task_id}-qa.md"
    qa_path.write_text(
        f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA {task_id}"
round: 1
---

# QA {task_id}
""",
        encoding="utf-8",
    )

    round_dir = repo_env / ".project" / "qa" / "validation-reports" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "implementation-report.md").write_text(
        """---
filesChanged:
  - src/demo.py
---
""",
        encoding="utf-8",
    )

    missing = build_reports_missing({"id": session_id})
    missing_validators = [
        item for item in missing if item.get("type") == "validator" and item.get("taskId") == task_id
    ]
    assert missing_validators == []

