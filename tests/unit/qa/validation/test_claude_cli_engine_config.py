from __future__ import annotations

from pathlib import Path

from edison.core.config.manager import ConfigManager
from edison.core.qa.engines.base import EngineConfig
from edison.core.qa.engines.cli import CLIEngine
from edison.core.registries.validators import ValidatorMetadata
from tests.helpers.paths import get_repo_root


def test_claude_cli_engine_places_prompt_after_all_flags() -> None:
    """Claude's `-p/--print` is a flag, not a prompt-arg subcommand.

    If we misconfigure it as a dash-subcommand, CLIEngine will place the prompt
    immediately after `-p` and then append flags afterwards, which breaks the
    real `claude` CLI parsing (options must appear before the prompt).
    """
    repo_root = get_repo_root()
    cfg = ConfigManager(repo_root=repo_root).get_all()
    engines = cfg.get("validation", {}).get("engines", {})
    claude_cfg = engines.get("claude-cli", {})

    engine = CLIEngine(EngineConfig.from_dict("claude-cli", dict(claude_cfg)), project_root=Path(repo_root))
    validator = ValidatorMetadata(id="global-claude", name="Claude", engine="claude-cli", wave="global")

    cmd = engine._build_command(validator, Path(repo_root), prompt_args=["PROMPT"])

    assert cmd[-1] == "PROMPT"
    assert "--output-format" in cmd
    assert "--permission-mode" in cmd
    assert "bypassPermissions" in cmd
    assert any(str(arg).startswith("--allowed-tools=") for arg in cmd)
    # `--disallowed-tools <tools...>` is variadic and would greedily consume the prompt
    # as an additional tool name, causing claude --print mode to error ("no prompt").
    assert "--disallowed-tools" not in cmd
    assert any(str(arg).startswith("--disallowed-tools=") for arg in cmd)
