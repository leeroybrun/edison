from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from edison.core.config.domains import OrchestratorConfig
from edison.core.schemas.validation import SchemaValidationError


def _write_schema(schemas_dir: Path) -> None:
    # Write a project-composed schema override where runtime schema loader reads.
    config_schemas_dir = schemas_dir / ".edison" / "_generated" / "schemas" / "config"
    config_schemas_dir.mkdir(parents=True, exist_ok=True)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Orchestrator Config",
        "type": "object",
        "required": ["default", "profiles"],
        "properties": {
            "default": {"type": "string"},
            "profiles": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": {
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "command": {"type": "string"},
                        "requires_tty": {"type": "boolean"},
                        "args": {"type": "array", "items": {"type": "string"}},
                        "cwd": {"type": "string"},
                        "type": {"type": "string"},
                        "env": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                        "initial_prompt": {
                            "type": "object",
                            "required": ["enabled"],
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "method": {
                                    "type": "string",
                                    "enum": ["stdin", "file", "arg", "env"],
                                },
                                "path": {"type": "string"},
                                "arg_flag": {"type": "string"},
                                "env_var": {"type": "string"},
                            },
                            "additionalProperties": False,
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        "additionalProperties": False,
    }
    from edison.core.utils.io import dump_yaml_string
    (config_schemas_dir / "orchestrator-config.schema.yaml").write_text(
        dump_yaml_string(schema, sort_keys=False), encoding="utf-8"
    )


def test_core_defaults_expose_profiles() -> None:
    cfg = OrchestratorConfig(validate=False)

    assert cfg.get_default_profile_name() == "claude"
    profiles = set(cfg.list_profiles())
    assert profiles == {"claude", "codex", "gemini", "happy", "mock"}

    claude = cfg.get_profile("claude")
    assert claude.get("command")
    assert claude.get("initial_prompt", {}).get("enabled") is True


def test_project_overlay_merges_bundled_defaults(tmp_path: Path) -> None:
    """Test that project config in .edison/config/ merges with bundled defaults.

    Architecture:
    - Bundled defaults: src/edison/data/config/ (always loaded first)
    - Project overrides: {repo_root}/.edison/config/ (merged on top)
    """
    project_config_dir = tmp_path / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)
    (project_config_dir / "orchestrator.yml").write_text(
        textwrap.dedent(
            """
            orchestrators:
              profiles:
                codex:
                  args:
                    - "+"
                    - "--extra-from-project"
                  env:
                    FROM: "project"
            """
        ),
        encoding="utf-8",
    )

    _write_schema(tmp_path)

    cfg = OrchestratorConfig(repo_root=tmp_path, validate=True)

    merged = cfg.get_profile("codex")
    # Args are merged: bundled defaults + project overlay (+ syntax appends)
    assert "--extra-from-project" in merged["args"]
    # Env from project overlay
    assert merged.get("env", {}).get("FROM") == "project"


def test_schema_validation_rejects_invalid_prompt_method(tmp_path: Path) -> None:
    """Test that invalid prompt method is rejected by schema validation.

    Note: Project config overrides bundled defaults. We override a bundled profile
    with an invalid initial_prompt.method value.
    """
    project_config_dir = tmp_path / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)
    (project_config_dir / "orchestrator.yaml").write_text(
        textwrap.dedent(
            """
            orchestrators:
              default: gemini
              profiles:
                gemini:
                  command: "gemini"
                  initial_prompt:
                    enabled: true
                    method: "socket"
            """
        ),
        encoding="utf-8",
    )

    _write_schema(tmp_path / ".edison" / "core" / "schemas")

    with pytest.raises(SchemaValidationError):
        OrchestratorConfig(repo_root=tmp_path, validate=True)


def test_template_expansion_replaces_tokens(tmp_path: Path) -> None:
    """Test that template variables in profile config are expanded correctly.

    Note: We add a custom 'templated' profile via project config overlay.
    """
    project_config_dir = tmp_path / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)
    (project_config_dir / "orchestrator.yaml").write_text(
        textwrap.dedent(
            """
            orchestrators:
              default: templated
              profiles:
                templated:
                  command: "echo"
                  args:
                    - "{session_id}"
                    - "{project_root}"
                    - "{session_worktree}"
                    - "{timestamp}"
                    - "{shortid}"
                  cwd: "{session_worktree}"
                  env:
                    SESSION: "{session_id}"
                  initial_prompt:
                    enabled: true
                    method: "file"
                    path: "{project_root}/guide.md"
            """
        ),
        encoding="utf-8",
    )

    _write_schema(tmp_path / ".edison" / "core" / "schemas")

    cfg = OrchestratorConfig(repo_root=tmp_path, validate=True)

    ctx = {
        "session_worktree": "/tmp/worktrees/session-42",
        "project_root": "/repo",
        "session_id": "session-42",
        "timestamp": "2025-11-22T10:00:00Z",
        "shortid": "abc123",
    }

    profile = cfg.get_profile("templated", context=ctx, expand=True)

    assert profile["args"][:3] == ["session-42", "/repo", "/tmp/worktrees/session-42"]
    assert profile["args"][3] == "2025-11-22T10:00:00Z"
    assert profile["args"][4] == "abc123"
    assert profile["cwd"] == "/tmp/worktrees/session-42"
    assert profile["env"]["SESSION"] == "session-42"
    assert profile["initial_prompt"]["path"] == "/repo/guide.md"

    # When timestamp/shortid are not provided, the expander should still inject values
    profile_generated = cfg.get_profile(
        "templated",
        context={
            "session_worktree": "/tmp/worktrees/session-99",
            "project_root": "/repo",
            "session_id": "session-99",
        },
        expand=True,
    )

    assert profile_generated["args"][0] == "session-99"
    assert profile_generated["cwd"] == "/tmp/worktrees/session-99"
    assert profile_generated["initial_prompt"]["path"].startswith("/repo")
    assert isinstance(profile_generated["args"][3], str)
    assert len(profile_generated["args"][4]) == 6
