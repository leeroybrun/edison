from __future__ import annotations

import yaml

from edison.core.qa.evidence import EvidenceService
from edison.core.registries.validators import ValidatorRegistry
from tests.helpers.env_setup import setup_project_root


def _seed_impl_report(project_root, task_id: str, files: list[str]) -> None:
    (project_root / ".project").mkdir(parents=True, exist_ok=True)
    ev = EvidenceService(task_id, project_root=project_root)
    ev.ensure_round(1)
    ev.write_implementation_report(
        {"summary": "test", "filesChanged": files},
        round_num=1,
    )


def _roster_ids(roster: dict) -> set[str]:
    ids: set[str] = set()
    for key in ("alwaysRequired", "triggeredBlocking", "triggeredOptional", "extraAdded"):
        for item in roster.get(key, []) or []:
            if isinstance(item, dict) and item.get("id"):
                ids.add(str(item["id"]))
    return ids


def test_docs_preset_excludes_critical_validators(tmp_path, monkeypatch) -> None:
    setup_project_root(monkeypatch, tmp_path)

    # Tests must not enforce bundled configuration. Define an explicit project config
    # to make preset inference + validator selection deterministic.
    cfg_dir = tmp_path / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "validation.yaml").write_text(
        yaml.safe_dump(
            {
                "validation": {
                    "validators": {
                        "global-claude": {"enabled": False},
                        "global-codex": {"enabled": False},
                        "v-global": {
                            "name": "Global",
                            "engine": "delegation",
                            "wave": "global",
                            "always_run": True,
                            "blocking": True,
                            "triggers": [],
                        },
                        "security": {
                            "name": "Security",
                            "engine": "delegation",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                        "performance": {
                            "name": "Performance",
                            "engine": "delegation",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                    },
                    "presets": {
                        "quick": {
                            "name": "quick",
                            "validators": [],
                            "required_evidence": [],
                            "blocking_validators": [],
                        },
                        "standard": {
                            "name": "standard",
                            "validators": ["security", "performance"],
                            "required_evidence": [],
                            "blocking_validators": ["security", "performance"],
                        },
                    },
                    "presetInference": {
                        "rules": [
                            {"patterns": ["docs/**"], "preset": "quick", "priority": 10},
                            {"patterns": ["src/**"], "preset": "standard", "priority": 20},
                        ]
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    task_id = "T-docs-1"
    _seed_impl_report(tmp_path, task_id, ["docs/README.md"])

    roster = ValidatorRegistry(project_root=tmp_path).build_execution_roster(task_id)
    ids = _roster_ids(roster)

    # always_run validators always run.
    assert "v-global" in ids

    # Docs-only changes should not schedule critical validators like security/performance by default.
    assert "security" not in ids
    assert "performance" not in ids


def test_source_preset_includes_critical_validators(tmp_path, monkeypatch) -> None:
    setup_project_root(monkeypatch, tmp_path)

    cfg_dir = tmp_path / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "validation.yaml").write_text(
        yaml.safe_dump(
            {
                "validation": {
                    "validators": {
                        "global-claude": {"enabled": False},
                        "global-codex": {"enabled": False},
                        "v-global": {
                            "name": "Global",
                            "engine": "delegation",
                            "wave": "global",
                            "always_run": True,
                            "blocking": True,
                            "triggers": [],
                        },
                        "security": {
                            "name": "Security",
                            "engine": "delegation",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                        "performance": {
                            "name": "Performance",
                            "engine": "delegation",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                    },
                    "presets": {
                        "quick": {
                            "name": "quick",
                            "validators": [],
                            "required_evidence": [],
                            "blocking_validators": [],
                        },
                        "standard": {
                            "name": "standard",
                            "validators": ["security", "performance"],
                            "required_evidence": [],
                            "blocking_validators": ["security", "performance"],
                        },
                    },
                    "presetInference": {
                        "rules": [
                            {"patterns": ["docs/**"], "preset": "quick", "priority": 10},
                            {"patterns": ["src/**"], "preset": "standard", "priority": 20},
                        ]
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    task_id = "T-src-1"
    _seed_impl_report(tmp_path, task_id, ["src/app.py"])

    roster = ValidatorRegistry(project_root=tmp_path).build_execution_roster(task_id)
    ids = _roster_ids(roster)

    assert "v-global" in ids

    # Source changes should select the standard preset and include security/performance.
    assert "security" in ids
    assert "performance" in ids


def test_default_preset_overrides_inference(tmp_path, monkeypatch) -> None:
    setup_project_root(monkeypatch, tmp_path)
    task_id = "T-default-preset-1"
    _seed_impl_report(tmp_path, task_id, ["src/app.py"])

    cfg_dir = tmp_path / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "validation.yaml").write_text(
        yaml.safe_dump(
            {
                "validation": {
                    "validators": {
                        "global-claude": {"enabled": False},
                        "global-codex": {"enabled": False},
                        "v-global": {
                            "name": "Global",
                            "engine": "delegation",
                            "wave": "global",
                            "always_run": True,
                            "blocking": True,
                            "triggers": [],
                        },
                        "security": {
                            "name": "Security",
                            "engine": "delegation",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                        "performance": {
                            "name": "Performance",
                            "engine": "delegation",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                    },
                    "defaultPreset": "custom-minimal",
                    "presets": {
                        "standard": {
                            "name": "standard",
                            "validators": ["security", "performance"],
                            "required_evidence": [],
                            "blocking_validators": ["security", "performance"],
                        },
                        "custom-minimal": {
                            "name": "custom-minimal",
                            # Intentionally empty: roster should still include always-run globals,
                            # but should NOT include standard preset validators.
                            "validators": [],
                            "required_evidence": [],
                            "blocking_validators": [],
                        },
                    },
                    "presetInference": {
                        "rules": [
                            {"patterns": ["src/**"], "preset": "standard", "priority": 10},
                        ]
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    roster = ValidatorRegistry(project_root=tmp_path).build_execution_roster(task_id)
    ids = _roster_ids(roster)

    assert "v-global" in ids

    # With defaultPreset set, we should NOT infer standard preset validators.
    assert "security" not in ids
    assert "performance" not in ids


def test_disabled_validator_is_excluded_from_roster(tmp_path, monkeypatch) -> None:
    setup_project_root(monkeypatch, tmp_path)
    task_id = "T-disabled-validator-1"
    _seed_impl_report(tmp_path, task_id, ["src/app.py"])

    cfg_dir = tmp_path / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "validation.yaml").write_text(
        yaml.safe_dump(
            {
                "validation": {
                    "validators": {
                        "global-claude": {"enabled": False},
                        "global-codex": {"enabled": False},
                        "v-disabled": {
                            "name": "Disabled",
                            "engine": "delegation",
                            "wave": "global",
                            "always_run": True,
                            "blocking": True,
                            "enabled": False,
                            "triggers": [],
                        },
                    },
                    "presets": {"standard": {"name": "standard", "validators": [], "required_evidence": [], "blocking_validators": []}},
                    "presetInference": {"rules": [{"patterns": ["src/**"], "preset": "standard", "priority": 10}]},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    roster = ValidatorRegistry(project_root=tmp_path).build_execution_roster(task_id)
    ids = _roster_ids(roster)

    assert "v-disabled" not in ids
