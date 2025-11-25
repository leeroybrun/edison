from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest


def _core_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "lib" / "config.py").exists():
            return parent
    raise AssertionError("cannot locate Edison core lib root")


def _ensure_core_on_path() -> None:
    core_root = _core_root()
    if str(core_root) not in sys.path:


def test_simple_delegation_hint_uses_task_type_rules(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    simple_delegation_hint should respect taskTypeRules when task doc declares a type.

    This mirrors the legacy QA helper behavior to ensure delegation logic resides
    in lib.qa.validator rather than orchestration scripts.
    """
    _ensure_core_on_path()
    import importlib

    task = importlib.import_module("lib.task")  # type: ignore[assignment]
    validator = importlib.import_module("lib.qa.validator")  # type: ignore[assignment]

    # Ensure task operates against the isolated project root
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(isolated_project_env))

    task_id = "9000-delegation-ui-component"
    # Create a real task file via task
    task.create_task(task_id, "Delegation smoke test")  # type: ignore[attr-defined]
    task_path = task.find_record(task_id, "task")  # type: ignore[attr-defined]

    # Append a minimal Task Type stanza expected by the parser
    original = task_path.read_text(encoding="utf-8")
    task_path.write_text(original + "\nTask Type: ui-component\n", encoding="utf-8")

    # Minimal delegation snippet with a ui-component rule
    delegation_cfg: Dict[str, Any] = {
        "taskTypeRules": {
            "ui-component": {
                "preferredModel": "claude",
                "preferredZenRole": "component-builder-nextjs",
            }
        },
        "filePatternRules": {},
        "subAgentDefaults": {},
    }

    hint = validator.simple_delegation_hint(  # type: ignore[attr-defined]
        task_id, delegation_cfg=delegation_cfg
    )
    assert hint is not None, "expected a delegation hint for ui-component task"
    assert hint.get("model") == "claude"
    assert hint.get("zenRole") == "component-builder-nextjs"


def test_build_validator_roster_categorizes_validators(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    build_validator_roster should categorize validators into expected buckets.

    This exercises the new lib.qa.validator implementation without mocks.
    """
    _ensure_core_on_path()
    import importlib

    task = importlib.import_module("lib.task")  # type: ignore[assignment]
    validator = importlib.import_module("lib.qa.validator")  # type: ignore[assignment]

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(isolated_project_env))

    # Create a simple task with primary files that will trigger specialized validators
    task_id = "9001-validator-roster"
    task.create_task(task_id, "Validator roster smoke test")  # type: ignore[attr-defined]
    task_path = task.find_record(task_id, "task")  # type: ignore[attr-defined]
    original = task_path.read_text(encoding="utf-8")
    task_path.write_text(
        original
        + "\nPrimary Files / Areas: app/api/leads/route.ts, app/example-app/page.tsx\n",
        encoding="utf-8",
    )

    validators_cfg: Dict[str, Any] = {
        "roster": {
            "global": [
                {
                    "id": "codex-global",
                    "name": "Codex Global",
                    "model": "codex",
                    "zenRole": "validator-codex-global",
                    "interface": "clink",
                    "priority": 1,
                }
            ],
            "critical": [
                {
                    "id": "security",
                    "name": "Security",
                    "model": "codex",
                    "zenRole": "validator-security",
                    "interface": "clink",
                    "priority": 2,
                    "blocksOnFail": True,
                }
            ],
            "specialized": [
                {
                    "id": "api",
                    "name": "API",
                    "model": "codex",
                    "zenRole": "validator-api",
                    "interface": "clink",
                    "priority": 3,
                    "blocksOnFail": False,
                    "triggers": ["**/api/**/*.ts"],
                },
                {
                    "id": "prisma",
                    "name": "Prisma",
                    "model": "codex",
                    "zenRole": "validator-prisma",
                    "interface": "clink",
                    "priority": 3,
                    "blocksOnFail": True,
                    "triggers": ["schema.prisma"],
                },
            ],
        }
    }

    roster = validator.build_validator_roster(  # type: ignore[attr-defined]
        task_id,
        session_id=None,
        validators_cfg=validators_cfg,
        manifest={"orchestration": {"maxConcurrentAgents": 2}},
    )

    always = roster.get("alwaysRequired") or []
    triggered_blocking = roster.get("triggeredBlocking") or []
    triggered_optional = roster.get("triggeredOptional") or []

    # Global + critical should be in alwaysRequired
    assert {v["id"] for v in always} == {"codex-global", "security"}
    # API validator should be triggered (optional) by primary files pattern
    assert {v["id"] for v in triggered_optional} == {"api"}
    # Database validator should not be triggered (no matching files)
    assert not triggered_blocking


def _repo_root_from_tests() -> Path:
    """Resolve repository root from the tests tree without PathResolver."""
    cur = Path(__file__).resolve()
    # .../example-project/.edison/core/tests/unit/lib/test_qa_validator.py
    return cur.parents[5]


def test_load_delegation_config_uses_yaml_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    qa.config.load_delegation_config should source data from YAML ConfigManager.

    The JSON delegation overlay under .agents/delegation/config.json only
    contains priority lists, while the core YAML config defines rich
    filePatternRules/taskTypeRules. This asserts YAML is used.
    """
    _ensure_core_on_path()
    import importlib

    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
    config = importlib.import_module("lib.qa.config")  # type: ignore[assignment]
    from edison.core.config import ConfigManager 
    repo_root = _repo_root_from_tests()
    cfg = ConfigManager(repo_root).load_config(validate=False)
    expected = cfg.get("delegation", {}) or {}

    loaded = config.load_delegation_config(repo_root=repo_root)  # type: ignore[attr-defined]

    assert loaded == expected


def test_load_validation_config_uses_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    """qa.config.load_validation_config should return the validation section from YAML."""
    _ensure_core_on_path()
    import importlib

    monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
    config = importlib.import_module("lib.qa.config")  # type: ignore[assignment]
    from edison.core.config import ConfigManager 
    repo_root = _repo_root_from_tests()
    cfg = ConfigManager(repo_root).load_config(validate=False)
    expected = cfg.get("validation", {}) or {}

    loaded = config.load_validation_config(repo_root=repo_root)  # type: ignore[attr-defined]

    assert loaded == expected
