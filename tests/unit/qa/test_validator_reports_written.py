from __future__ import annotations

from pathlib import Path

import yaml

from edison.core.qa.engines import ValidationExecutor
from edison.core.qa.evidence import EvidenceService
from edison.core.registries.validators import ValidatorRegistry
from helpers.cache_utils import reset_edison_caches


def test_validation_executor_writes_validator_report_json(isolated_project_env):
    root: Path = isolated_project_env

    # Project override: add a tiny executable validator backed by /bin/echo.
    # This avoids external CLIs and keeps the test deterministic.
    cfg_path = root / ".edison" / "config" / "validators.yaml"
    cfg = {
        "validation": {
            "engines": {
                "echo-cli": {
                    "type": "cli",
                    "command": "/bin/echo",
                    "subcommand": "APPROVED",
                    "output_flags": [],
                    "read_only_flags": [],
                    "response_parser": "plain_text",
                }
            },
            "validators": {
                "echo": {
                    "name": "Echo Validator",
                    "engine": "echo-cli",
                    "fallback_engine": None,
                    "prompt": "",
                    "wave": "critical",
                    "always_run": True,
                    "blocking": True,
                    "timeout": 5,
                    "context7_required": False,
                    "context7_packages": [],
                    "triggers": ["*"],
                    "focus": [],
                }
            },
        }
    }
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    # The test harness may have already loaded and cached config during fixture setup.
    # Clear caches so our newly-written override is picked up.
    reset_edison_caches()

    task_id = "task-echo-demo"
    executor = ValidationExecutor(project_root=root, max_workers=1)

    # Sanity-check: our validator is visible to the registry in this isolated env.
    vreg = ValidatorRegistry(project_root=root)
    assert vreg.get("echo") is not None

    # Execute only our test validator (avoid running the full default roster).
    result = executor.execute(
        task_id=task_id,
        session_id="sess-echo",
        worktree_path=root,
        wave="critical",
        validators=["echo"],
        parallel=False,
    )

    assert result.total_validators == 1
    assert result.waves
    assert result.waves[0].validators[0].validator_id == "echo"

    ev = EvidenceService(task_id, project_root=root)
    report = ev.read_validator_report("echo")
    assert report, "Expected validator report JSON to be written"
    assert report["taskId"] == task_id
    assert report["validatorId"] == "echo"
    assert report["verdict"] in ("approve", "approved", "pass", "passed", "pending", "blocked", "reject")

