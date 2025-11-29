from __future__ import annotations
from helpers.io_utils import write_yaml, write_json

from pathlib import Path
import yaml

import pytest

from edison.core.setup import SetupDiscovery, SetupQuestionnaire

FULL_SETUP = {
    "setup": {
        "version": "1.0",
        "modes": [
            {"id": "basic", "name": "Basic Setup", "description": "Essential configuration for getting started"},
            {"id": "advanced", "name": "Advanced Setup", "description": "Full configuration including paths, state machine, validators"},
        ],
        "basic": [
            {
                "id": "project_name",
                "prompt": "Project name",
                "type": "string",
                "default": "{{ detected.project_name }}",
                "required": True,
                "help": "Name of your project (used in documentation and config)",
            },
            {
                "id": "project_type",
                "prompt": "Project type",
                "type": "choice",
                "source": "static",
                "options": [
                    "Next.js Full-Stack",
                    "Fastify API",
                    "React App",
                    "Python Library",
                    "Node.js Library",
                    "Go Application",
                    "Rust Project",
                    "Other",
                ],
                "default": "Other",
                "help": "Type of project (helps select appropriate packs)",
            },
            {
                "id": "packs",
                "prompt": "Technology packs",
                "type": "multiselect",
                "source": "discover_packs",
                "default": [],
                "help": "Select technology packs to enable (auto-discovered from .edison/packs/)",
            },
            {
                "id": "orchestrators",
                "prompt": "IDE orchestrators",
                "type": "multiselect",
                "source": "discover_orchestrators",
                "default": ["claude"],
                "help": "Select which IDE integrations to generate",
            },
            {
                "id": "database",
                "prompt": "Database",
                "type": "choice",
                "source": "static",
                "options": ["PostgreSQL", "MySQL", "SQLite", "MongoDB", "None"],
                "default": "None",
            },
            {
                "id": "auth_provider",
                "prompt": "Authentication",
                "type": "choice",
                "source": "static",
                "options": ["better-auth", "next-auth", "clerk", "auth0", "Custom", "None"],
                "default": "None",
            },
            {
                "id": "enable_worktrees",
                "prompt": "Enable git worktrees?",
                "type": "boolean",
                "default": False,
                "help": "Use git worktrees for session isolation",
            },
            {"id": "ci_lint", "prompt": "Lint command", "type": "string", "default": "npm run lint"},
            {"id": "ci_test", "prompt": "Test command", "type": "string", "default": "npm test"},
            {"id": "ci_build", "prompt": "Build command", "type": "string", "default": "npm run build"},
            {"id": "ci_type_check", "prompt": "Type check command", "type": "string", "default": "npm run type-check"},
        ],
        "advanced": [
            {
                "id": "project_config_dir",
                "prompt": "Project config directory",
                "type": "string",
                "default": ".agents",
                "help": "Where to store Edison project configuration",
                "validation": "^[.a-zA-Z0-9_-]+$",
            },
            {
                "id": "project_management_dir",
                "prompt": "Project management directory",
                "type": "string",
                "default": ".project",
                "help": "Where to store sessions, tasks, and QA artifacts",
                "validation": "^[.a-zA-Z0-9_-]+$",
            },
            {
                "id": "task_states",
                "prompt": "Task state folders",
                "type": "list",
                "default": ["todo", "wip", "blocked", "done", "validated"],
                "help": "Folder names for task states",
            },
            {
                "id": "session_states",
                "prompt": "Session state folders",
                "type": "list",
                "default": ["active", "closing", "recovery", "waiting", "wip"],
                "help": "Folder names for session states",
            },
            {
                "id": "validators",
                "prompt": "Enable validators",
                "type": "multiselect",
                "source": "discover_validators",
                "default": [],
                "help": "Select which validators to enable (core + pack validators)",
            },
            {
                "id": "agents",
                "prompt": "Enable agents",
                "type": "multiselect",
                "source": "discover_agents",
                "default": [],
                "help": "Select which agents to enable (core + pack agents)",
            },
            {
                "id": "tdd_enforcement",
                "prompt": "TDD enforcement level",
                "type": "choice",
                "source": "static",
                "options": ["strict", "warn", "off"],
                "default": "warn",
            },
            {
                "id": "coverage_threshold",
                "prompt": "Code coverage threshold (%)",
                "type": "integer",
                "default": 90,
                "validation": "0-100",
            },
        ],
    },
    "discovery": {
        "packs": {"directory": ".edison/packs", "pattern": "*/config.yml"},
        "orchestrators": {
            "config_file": ".edison/core/config/orchestrators.yaml",
            "fallback": ["claude", "cursor", "codex"],
        },
        "validators": {
            "core_config": ".edison/core/config/validators.yaml",
            "pack_pattern": ".edison/packs/*/config/validators.yml",
        },
        "agents": {
            "core_config": ".edison/core/config/agents.yaml",
            "pack_pattern": ".edison/packs/*/config/agents.yml",
        },
    },
}

def _write_setup(repo_root: Path) -> None:
    path = repo_root / ".edison" / "core" / "config" / "setup.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(FULL_SETUP), encoding="utf-8")

def _build_questionnaire(repo: Path) -> SetupQuestionnaire:
    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    return SetupQuestionnaire(repo_root=repo, edison_core=repo / ".edison" / "core", discovery=discovery)

def test_basic_mode_non_interactive_uses_defaults(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _write_setup(repo)
    write_json(repo / "package.json", {"name": "demo-app", "dependencies": {"react": "18.0.0"}})

    q = _build_questionnaire(repo)
    result = q.run(mode="basic", assume_yes=True)

    assert result["project_name"] == "demo-app"
    assert result["project_type"] == "Other"
    assert result["packs"] == []
    assert result["orchestrators"] == ["claude"]
    assert result["enable_worktrees"] is False

def test_advanced_mode_includes_additional_questions(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _write_setup(repo)
    write_json(repo / "package.json", {"name": "demo-app"})
    write_yaml(repo / ".edison" / "core" / "config" / "validators.yaml", {"validation": {"roster": {"global": [{"id": "core-val"}]}}})
    write_yaml(repo / ".edison" / "core" / "config" / "agents.yaml", {"agents": [{"id": "core-agent"}]})

    q = _build_questionnaire(repo)
    result = q.run(mode="advanced", assume_yes=True)

    for key in [
        "project_config_dir",
        "project_management_dir",
        "task_states",
        "session_states",
        "validators",
        "agents",
        "tdd_enforcement",
        "coverage_threshold",
    ]:
        assert key in result
    assert result["task_states"] == ["todo", "wip", "blocked", "done", "validated"]
    assert result["coverage_threshold"] == 90

def test_validation_rejects_invalid_values(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _write_setup(repo)
    q = _build_questionnaire(repo)

    with pytest.raises(ValueError):
        q.run(mode="basic", provided_answers={"project_type": "Django"}, assume_yes=True)

    with pytest.raises(ValueError):
        q.run(mode="advanced", provided_answers={"coverage_threshold": 120}, assume_yes=True)

def test_multiselect_enforces_discovered_options(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _write_setup(repo)
    packs_dir = repo / ".edison" / "packs"
    write_yaml(packs_dir / "alpha" / "config.yml", {"name": "alpha"})
    write_yaml(packs_dir / "beta" / "config.yml", {"name": "beta"})
    write_yaml(repo / ".edison" / "core" / "config" / "validators.yaml", {"validation": {"roster": {"global": [{"id": "core-val"}]}}})
    write_yaml(repo / ".edison" / "packs" / "alpha" / "config" / "validators.yml", {"validation": {"roster": {"global": [{"id": "pack-val"}]}}})

    q = _build_questionnaire(repo)
    result = q.run(
        mode="advanced",
        provided_answers={
            "packs": ["alpha"],
            "validators": ["core-val", "pack-val"],
            "agents": [],
        },
        assume_yes=True,
    )
    assert result["packs"] == ["alpha"]
    assert result["validators"] == ["core-val", "pack-val"]

    with pytest.raises(ValueError):
        q.run(mode="advanced", provided_answers={"packs": ["ghost"]}, assume_yes=True)
