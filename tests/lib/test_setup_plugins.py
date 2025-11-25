from __future__ import annotations

from pathlib import Path
import yaml

from edison.core.setup.discovery import SetupDiscovery
from edison.core.setup.questionnaire import SetupQuestionnaire


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _seed_core_setup(repo_root: Path) -> None:
    setup_cfg = {
        "setup": {
            "version": "1.0",
            "modes": [
                {"id": "basic", "name": "Basic", "description": "Basic"},
                {"id": "advanced", "name": "Advanced", "description": "Advanced"},
            ],
            "basic": [
                {
                    "id": "project_name",
                    "prompt": "Project name",
                    "type": "string",
                    "default": "demo-app",
                },
                {
                    "id": "project_type",
                    "prompt": "Project type",
                    "type": "string",
                    "default": "Other",
                },
                {
                    "id": "packs",
                    "prompt": "Technology packs",
                    "type": "multiselect",
                    "source": "discover_packs",
                    "default": [],
                },
            ],
            "advanced": [
                {"id": "advanced_flag", "prompt": "Advanced flag", "type": "boolean", "default": False}
            ],
        },
        "discovery": {
            "packs": {"directory": ".edison/packs", "pattern": "*/config.yml"},
            "orchestrators": {"fallback": []},
            "validators": {"core_config": ".edison/core/config/validators.yaml", "pack_pattern": ".edison/packs/*/config/validators.yml"},
            "agents": {"core_config": ".edison/core/config/agents.yaml", "pack_pattern": ".edison/packs/*/config/agents.yml"},
        },
    }

    _write_yaml(repo_root / ".edison" / "core" / "config" / "setup.yaml", setup_cfg)


def _write_pack(repo_root: Path, name: str, setup_data: dict | None = None) -> Path:
    pack_dir = repo_root / ".edison" / "packs" / name
    (pack_dir / "config").mkdir(parents=True, exist_ok=True)
    (pack_dir / "config.yml").write_text(f"name: {name}\n", encoding="utf-8")
    if setup_data:
        _write_yaml(pack_dir / "config" / "setup.yml", setup_data)
    return pack_dir


def _build_questionnaire(repo_root: Path) -> SetupQuestionnaire:
    discovery = SetupDiscovery(repo_root / ".edison" / "core", repo_root)
    return SetupQuestionnaire(repo_root=repo_root, edison_core=repo_root / ".edison" / "core", discovery=discovery)


def test_discover_pack_setup_questions_merges_selected_packs(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_core_setup(repo)

    ts_setup = {
        "setup": {
            "questions": [
                {
                    "id": "typescript_strict",
                    "prompt": "Enable TypeScript strict mode?",
                    "type": "boolean",
                    "default": True,
                    "mode": "basic",
                    "depends_on": [{"pack": "typescript", "enabled": True}],
                },
                {
                    "id": "typescript_target",
                    "prompt": "TypeScript compilation target",
                    "type": "choice",
                    "options": ["ES2020", "ES2021"],
                    "default": "ES2021",
                    "mode": "advanced",
                    "depends_on": [{"pack": "typescript", "enabled": True}],
                },
            ]
        }
    }

    react_setup = {
        "setup": {
            "questions": [
                {
                    "id": "react_version",
                    "prompt": "React version",
                    "type": "choice",
                    "options": ["18", "19-rc"],
                    "default": "18",
                    "mode": "advanced",
                    "depends_on": [{"pack": "react", "enabled": True}],
                }
            ]
        }
    }

    _write_pack(repo, "typescript", ts_setup)
    _write_pack(repo, "react", react_setup)

    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    ids = [q["id"] for q in discovery.discover_pack_setup_questions(["typescript", "react"])]

    assert ids == ["typescript_strict", "typescript_target", "react_version"]


def test_dependencies_require_selected_pack(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_core_setup(repo)

    react_setup = {
        "setup": {
            "questions": [
                {
                    "id": "react_strict_mode",
                    "prompt": "Enable React StrictMode?",
                    "type": "boolean",
                    "default": True,
                    "depends_on": [{"pack": "react", "enabled": True}],
                }
            ]
        }
    }

    _write_pack(repo, "react", react_setup)

    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    questions = discovery.discover_pack_setup_questions(["typescript"])  # react not selected

    assert questions == []


def test_questionnaire_runs_pack_questions_after_pack_selection_basic(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_core_setup(repo)

    ts_setup = {
        "setup": {
            "questions": [
                {"id": "ts_basic", "prompt": "TS basic", "type": "boolean", "default": True, "mode": "basic"},
                {"id": "ts_adv", "prompt": "TS advanced", "type": "string", "default": "adv", "mode": "advanced"},
            ]
        }
    }

    _write_pack(repo, "typescript", ts_setup)

    q = _build_questionnaire(repo)
    answers = q.run(mode="basic", provided_answers={"packs": ["typescript"]}, assume_yes=True)

    assert answers["packs"] == ["typescript"]
    assert answers["ts_basic"] is True
    assert "ts_adv" not in answers  # advanced question should be skipped in basic mode


def test_questionnaire_runs_pack_questions_in_advanced_mode(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_core_setup(repo)

    ts_setup = {
        "setup": {
            "questions": [
                {"id": "ts_basic", "prompt": "TS basic", "type": "boolean", "default": True, "mode": "basic"},
                {"id": "ts_adv", "prompt": "TS advanced", "type": "string", "default": "adv", "mode": "advanced"},
            ]
        }
    }

    _write_pack(repo, "typescript", ts_setup)

    q = _build_questionnaire(repo)
    answers = q.run(mode="advanced", provided_answers={"packs": ["typescript"]}, assume_yes=True)

    assert answers["ts_basic"] is True
    assert answers["ts_adv"] == "adv"


def test_render_config_template_includes_pack_config(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_core_setup(repo)

    ts_setup = {
        "setup": {
            "questions": [
                {"id": "typescript_strict", "prompt": "TS strict", "type": "boolean", "default": False},
                {"id": "typescript_target", "prompt": "TS target", "type": "choice", "options": ["ES2020", "ESNext"], "default": "ESNext"},
            ],
            "config_template": {
                "typescript": {
                    "strict": "{{ typescript_strict }}",
                    "target": "{{ typescript_target }}",
                }
            },
        }
    }

    react_setup = {
        "setup": {
            "questions": [
                {"id": "react_version", "prompt": "React version", "type": "choice", "options": ["18", "19"], "default": "19"},
            ],
            "config_template": {"react": {"version": "{{ react_version }}"}},
        }
    }

    _write_pack(repo, "typescript", ts_setup)
    _write_pack(repo, "react", react_setup)

    q = _build_questionnaire(repo)
    answers = {
        "project_name": "demo-app",
        "project_type": "Other",
        "packs": ["typescript", "react"],
        "typescript_strict": True,
        "typescript_target": "ES2020",
        "react_version": "18",
    }

    rendered = q.render_config_template(answers)
    cfg = yaml.safe_load(rendered)

    pack_cfg = cfg.get("pack_config") or {}
    assert pack_cfg["typescript"]["strict"] is True
    assert pack_cfg["typescript"]["target"] == "ES2020"
    assert pack_cfg["react"]["version"] == "18"


def test_missing_pack_setup_file_is_skipped(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_core_setup(repo)

    _write_pack(repo, "typescript", None)  # no setup.yml present

    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    questions = discovery.discover_pack_setup_questions(["typescript"])

    assert questions == []
