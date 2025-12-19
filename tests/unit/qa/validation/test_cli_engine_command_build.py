from __future__ import annotations

from pathlib import Path

from edison.core.qa.engines.base import EngineConfig
from edison.core.qa.engines.cli import CLIEngine
from edison.core.registries.validators import ValidatorMetadata


def test_cli_engine_build_command_includes_pre_flags_before_subcommand() -> None:
    cfg = EngineConfig.from_dict(
        "codex-cli",
        {
            "type": "cli",
            "command": "codex",
            "pre_flags": ["--ask-for-approval", "never", "--sandbox", "workspace-write"],
            "subcommand": "exec",
            "output_flags": ["--json"],
            "prompt_mode": "stdin",
            "stdin_prompt_arg": "-",
            "response_parser": "codex",
        },
    )
    engine = CLIEngine(cfg)
    validator = ValidatorMetadata(id="security", name="Security", engine="codex-cli", wave="critical")

    cmd = engine._build_command(validator, Path("/tmp"), prompt_args=["-"])

    assert cmd[:7] == [
        "codex",
        "--ask-for-approval",
        "never",
        "--sandbox",
        "workspace-write",
        "exec",
        "--json",
    ]


def test_cli_engine_places_prompt_arg_immediately_after_dash_subcommand() -> None:
    """Some CLIs use a flag-like 'subcommand' (e.g. -p) that requires an argument.

    In that case, the prompt must come immediately after the dash-subcommand and
    before any output flags.
    """
    cfg = EngineConfig.from_dict(
        "gemini-cli",
        {
            "type": "cli",
            "command": "gemini",
            "subcommand": "-p",
            "output_flags": ["--output-format", "json"],
            "prompt_mode": "arg",
            "response_parser": "gemini",
        },
    )
    engine = CLIEngine(cfg)
    validator = ValidatorMetadata(id="global-gemini", name="Gemini", engine="gemini-cli", wave="critical")

    cmd = engine._build_command(validator, Path("/tmp"), prompt_args=["PROMPT"])
    assert cmd[:5] == ["gemini", "-p", "PROMPT", "--output-format", "json"]
