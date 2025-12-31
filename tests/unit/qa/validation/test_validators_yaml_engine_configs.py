from __future__ import annotations

from pathlib import Path

from edison.core.qa.engines.registry import EngineRegistry


def test_validators_yaml_configures_gemini_cli_with_positional_prompt(
    isolated_project_env: Path,
) -> None:
    """Gemini CLI deprecates `-p/--prompt`; prefer positional prompt content."""
    registry = EngineRegistry(project_root=isolated_project_env)
    engine = registry._get_or_create_engine("gemini-cli")
    assert engine is not None
    assert engine.config.subcommand == ""


def test_validators_yaml_does_not_run_claude_in_plan_mode(
    isolated_project_env: Path,
) -> None:
    registry = EngineRegistry(project_root=isolated_project_env)
    engine = registry._get_or_create_engine("claude-cli")
    assert engine is not None
    flags = [str(v).lower() for v in (engine.config.read_only_flags or [])]
    assert "plan" not in flags
