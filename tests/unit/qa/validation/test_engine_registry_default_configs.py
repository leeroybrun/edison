from __future__ import annotations

from pathlib import Path

from edison.core.qa.engines.registry import EngineRegistry


def test_engine_registry_default_engine_config_for_gemini_uses_positional_prompt(
    isolated_project_env: Path,
) -> None:
    registry = EngineRegistry(project_root=isolated_project_env)
    cfg = registry._create_default_engine_config("gemini-cli")
    assert cfg is not None

    # Gemini CLI deprecates `-p/--prompt`; prefer positional prompt content.
    assert cfg.subcommand == ""
    assert cfg.prompt_mode == "arg"


def test_engine_registry_default_engine_config_for_claude_uses_arg_prompt_mode(
    isolated_project_env: Path,
) -> None:
    registry = EngineRegistry(project_root=isolated_project_env)
    cfg = registry._create_default_engine_config("claude-cli")
    assert cfg is not None

    # Claude CLI `-p` expects prompt content, not a file path.
    assert cfg.subcommand == "-p"
    assert cfg.prompt_mode == "arg"

    # Validators must be able to read repo/evidence non-interactively.
    # Plan mode blocks Read/Bash tool use and causes false "blocked" outputs.
    assert "plan" not in [str(v).lower() for v in (cfg.read_only_flags or [])]


def test_engine_registry_default_engine_config_for_codex_emits_jsonl(
    isolated_project_env: Path,
) -> None:
    registry = EngineRegistry(project_root=isolated_project_env)
    cfg = registry._create_default_engine_config("codex-cli")
    assert cfg is not None

    # Codex parser expects JSONL events; the engine must request JSON output.
    assert "--json" in (cfg.output_flags or [])
