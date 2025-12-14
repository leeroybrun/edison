"""Session-next reportsMissing should be trigger-aware (roster-driven), not "all blocking".

This test protects the coherence between:
- ValidatorRegistry.build_execution_roster (canonical trigger logic)
- session-next build_reports_missing (missing validator/context7 evidence reporting)
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
    (repo / ".project" / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "meta").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

    # Required task template path
    (repo / ".project" / "tasks" / "TEMPLATE.md").write_text("# TEMPLATE\n", encoding="utf-8")

    # Config: tasks paths + workflow state machine (minimal)
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

    # Custom validators to make the roster deterministic for this test.
    # - test-api triggers on apps/api/**
    # - test-react triggers on apps/dashboard/**
    # Only test-api should be required by the roster for the given implementation report.
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
                        "context7_packages": ["fastify"],
                    },
                    "test-react": {
                        "name": "Test React",
                        "engine": "delegation",
                        "wave": "critical",
                        "blocking": True,
                        "always_run": False,
                        "triggers": ["apps/dashboard/**/*"],
                        "context7_required": True,
                        "context7_packages": ["react"],
                    },
                }
            }
        },
    )

    setup_project_root(monkeypatch, repo)
    reset_all_and_reload()
    return repo


def test_build_reports_missing_uses_triggered_blocking_validators(repo_env: Path) -> None:
    from edison.core.session.next.actions import build_reports_missing

    session_id = "s1"
    task_id = "task-1"

    # Task in session (used by TaskRepository.find_by_session)
    task_path = repo_env / ".project" / "tasks" / "todo" / f"{task_id}.md"
    task_path.write_text(
        f"""---
id: "{task_id}"
title: "Demo"
session_id: "{session_id}"
---

# Demo
""",
        encoding="utf-8",
    )

    # QA in an active state (qa/todo) so validator reports are expected.
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

    # Evidence round with implementation report that triggers ONLY test-api.
    round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "implementation-report.json").write_text(
        '{"filesChanged":["apps/api/server.ts"]}',
        encoding="utf-8",
    )

    # No validator-*-report.json files exist yet.
    missing = build_reports_missing({"id": session_id})

    missing_validators = {
        item["validatorId"]
        for item in missing
        if item.get("type") == "validator" and item.get("taskId") == task_id
    }

    # Trigger-aware: test-api must be required, test-react must NOT be required.
    assert "test-api" in missing_validators
    assert "test-react" not in missing_validators

    # Context7 requirement is derived from the roster (not from legacy validators/config.json).
    ctx7_missing = [
        item for item in missing if item.get("type") == "context7" and item.get("taskId") == task_id
    ]
    assert ctx7_missing, "Expected Context7 missing entry when required packages are configured"
    assert "fastify" in (ctx7_missing[0].get("packages") or [])

