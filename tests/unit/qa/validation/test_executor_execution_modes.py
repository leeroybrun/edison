from __future__ import annotations

from pathlib import Path

import yaml

from edison.core.qa.engines import ValidationExecutor


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_can_execute_validator_false_when_only_delegation_fallback(isolated_project_env: Path) -> None:
    """can_execute_validator() must mean 'can run via CLI', not 'can delegate'.

    A delegated fallback engine (zen-mcp) is always available, but that does NOT
    mean we can execute validators directly.
    """
    repo = isolated_project_env
    cfg_dir = repo / ".edison" / "config"

    _write_yaml(
        cfg_dir / "qa.yaml",
        {
            "orchestration": {
                "allowCliEngines": False,
            }
        },
    )
    _write_yaml(
        cfg_dir / "validators.yaml",
        {
            "validation": {
                "engines": {
                    "git-cli": {
                        "type": "cli",
                        "command": "git",
                        "subcommand": "--version",
                        "output_flags": [],
                        "read_only_flags": [],
                        "response_parser": "plain_text",
                    },
                },
                "validators": {
                    "git-validator": {
                        "name": "Git Validator (test)",
                        "engine": "git-cli",
                        "fallback_engine": "zen-mcp",
                        "wave": "critical",
                        "always_run": True,
                        "blocking": True,
                    }
                },
            }
        },
    )

    # Ensure ConfigManager picks up the just-written overrides (tests run in one process).
    from tests.helpers.cache_utils import reset_edison_caches
    reset_edison_caches()

    executor = ValidationExecutor(project_root=repo)
    assert executor.can_execute_validator("git-validator") is False


def test_executor_marks_delegated_when_cli_disabled(isolated_project_env: Path) -> None:
    """When CLI engines are disabled, execution should surface validators as delegated."""
    repo = isolated_project_env
    cfg_dir = repo / ".edison" / "config"

    _write_yaml(
        cfg_dir / "qa.yaml",
        {
            "orchestration": {
                "allowCliEngines": False,
            }
        },
    )
    _write_yaml(
        cfg_dir / "validators.yaml",
        {
            "validation": {
                "engines": {
                    "git-cli": {
                        "type": "cli",
                        "command": "git",
                        "subcommand": "--version",
                        "output_flags": [],
                        "read_only_flags": [],
                        "response_parser": "plain_text",
                    },
                },
                "validators": {
                    "git-validator": {
                        "name": "Git Validator (test)",
                        "engine": "git-cli",
                        "fallback_engine": "zen-mcp",
                        "wave": "critical",
                        "always_run": True,
                        "blocking": True,
                    }
                },
                "waves": [{"name": "critical"}],
            }
        },
    )

    # Ensure ConfigManager picks up the just-written overrides (tests run in one process).
    from tests.helpers.cache_utils import reset_edison_caches
    reset_edison_caches()

    executor = ValidationExecutor(project_root=repo, max_workers=1)
    result = executor.execute(task_id="T001", session_id="S001", wave="critical", parallel=False)
    assert "git-validator" in (result.delegated_validators or [])
    assert result.all_blocking_passed is False
    assert result.waves and result.waves[0].blocking_passed is False

    evidence_dir = repo / ".project" / "qa" / "validation-evidence" / "T001"
    round_dir = evidence_dir / f"round-{result.round_num}"
    assert (round_dir / "delegation-git-validator.md").exists()
