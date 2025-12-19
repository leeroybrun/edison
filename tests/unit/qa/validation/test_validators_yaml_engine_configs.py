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
    assert getattr(engine, "config").subcommand == ""

