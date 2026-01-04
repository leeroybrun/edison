from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_bundle_approval_ignores_validator_filter(isolated_project_env: Path) -> None:
    """Bundle approval must not be bypassable via `--validators`.

    `--validators` is an execution filter, not an approval scope. The bundle-approved
    decision must always be computed against the full blocking roster.
    """
    repo = isolated_project_env
    cfg_dir = repo / ".edison" / "config"

    # Override validators to a minimal deterministic set.
    _write_yaml(
        cfg_dir / "validators.yaml",
        {
            "validation": {
                "validators": {
                    "v1": {
                        "name": "V1",
                        "engine": "pal-mcp",
                        "fallback_engine": "pal-mcp",
                        "wave": "critical",
                        "always_run": True,
                        "blocking": True,
                        "triggers": ["*"],
                    },
                    "v2": {
                        "name": "V2",
                        "engine": "pal-mcp",
                        "fallback_engine": "pal-mcp",
                        "wave": "critical",
                        "always_run": True,
                        "blocking": True,
                        "triggers": ["*"],
                    },
                },
                "waves": [{"name": "critical"}],
            }
        },
    )

    from tests.helpers.cache_utils import reset_edison_caches
    reset_edison_caches()

    # Create a task file so the manifest builder can resolve it.
    task_dir = repo / ".project" / "tasks" / "done"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "T001.md").write_text(
        "---\n"
        "id: T001\n"
        "title: T001\n"
        "owner: test\n"
        "created_at: '2025-12-15T00:00:00Z'\n"
        "updated_at: '2025-12-15T00:00:00Z'\n"
        "---\n\n"
        "# T001\n",
        encoding="utf-8",
    )

    # Create only ONE validator report (approve v1), leaving v2 missing.
    from edison.core.qa.evidence import EvidenceService

    ev = EvidenceService("T001", project_root=repo)
    ev.ensure_round(1)
    ev.write_validator_report(
        "v1",
        {
            "taskId": "T001",
            "round": 1,
            "validatorId": "v1",
            "model": "test",
            "palRole": "validator-v1",
            "verdict": "approve",
            "findings": [],
            "strengths": [],
            "context7Used": False,
            "context7Packages": [],
            "evidenceReviewed": [],
            "summary": "ok",
            "followUpTasks": [],
            "tracking": {
                "processId": 1,
                "hostname": "test",
                "startedAt": "2025-12-15T00:00:00Z",
                "completedAt": "2025-12-15T00:00:00Z",
            },
        },
        round_num=1,
    )

    from edison.cli.qa import validate as validate_cli
    from edison.core.registries.validators import ValidatorRegistry

    args = argparse.Namespace(
        task_id="T001",
        session=None,
        round=1,
        wave=None,
        validators=["v1"],
        add_validators=None,
        blocking_only=False,
        execute=False,
        check_only=False,
        sequential=True,
        dry_run=False,
        max_workers=1,
        json=True,
        repo_root=str(repo),
    )

    bundle, approved, cluster_missing = validate_cli._compute_bundle_summary(
        args=args,
        repo_root=repo,
        session_id=None,
        validator_registry=ValidatorRegistry(project_root=repo),
        round_num=1,
        root_task_id="T001",
        scope_used="task",
        cluster_task_ids=["T001"],
        manifest_tasks=[{"taskId": "T001"}],
    )

    assert approved is False
    assert bundle.get("approved") is False
    assert cluster_missing.get("T001") and "v2" in cluster_missing["T001"]
