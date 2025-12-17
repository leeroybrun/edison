"""Context7 evidence guard must ignore the '+' sentinel in context7_packages.

P0: Some pack validator configs use context7_packages like ['+', 'next'].
The '+' entry is not a real package and must not require a marker file like
context7-+.txt.
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

    (repo / ".project" / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "meta").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)
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
                    "evidenceSubdir": "validation-evidence",
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
                        "done": {"allowed_transitions": []},
                    }
                },
                "qa": {
                    "states": {
                        "todo": {"initial": True, "allowed_transitions": []},
                        "done": {"allowed_transitions": []},
                    }
                },
            },
        },
    )

    write_yaml(
        cfg_dir / "validation.yaml",
        {
            "validation": {
                "validators": {
                    "test-api": {
                        "name": "Test API",
                        "engine": "delegation",
                        "wave": "critical",
                        "blocking": True,
                        "always_run": False,
                        "triggers": ["apps/api/**/*"],
                        "context7_required": True,
                        "context7_packages": ["+", "fastify"],
                    }
                }
            }
        },
    )

    setup_project_root(monkeypatch, repo)
    reset_all_and_reload()
    return repo


def test_reports_missing_context7_packages_excludes_plus(repo_env: Path) -> None:
    from edison.core.session.next.actions import build_reports_missing

    session_id = "s1"
    task_id = "task-1"

    (repo_env / ".project" / "tasks" / "todo" / f"{task_id}.md").write_text(
        f"""---
id: "{task_id}"
title: "Demo"
session_id: "{session_id}"
---

# Demo
""",
        encoding="utf-8",
    )

    (repo_env / ".project" / "qa" / "todo" / f"{task_id}-qa.md").write_text(
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

    round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "implementation-report.md").write_text(
        """---
filesChanged:
  - apps/api/server.ts
---
""",
        encoding="utf-8",
    )

    missing = build_reports_missing({"id": session_id})

    ctx7_missing = [
        item for item in missing if item.get("type") == "context7" and item.get("taskId") == task_id
    ]
    assert ctx7_missing

    pkgs = ctx7_missing[0].get("packages") or []
    assert "fastify" in pkgs
    assert "+" not in pkgs

