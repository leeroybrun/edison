"""Tests for OpenCode agent and command generation (task 078)."""
from __future__ import annotations

import argparse
from pathlib import Path


def _parse_setup_args(repo_root: Path, *argv: str):
    from edison.cli.opencode.setup import register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    return parser.parse_args([*argv, "--repo-root", str(repo_root), "--json"])


def test_opencode_setup_generates_agent_files(isolated_project_env: Path) -> None:
    """Setup should generate Edison agent markdown files under .opencode/agent/."""
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--yes", "--agents")
    rc = main(args)
    assert rc == 0

    agent_dir = isolated_project_env / ".opencode" / "agent"
    assert agent_dir.exists()

    # Check expected agent files exist
    orchestrator = agent_dir / "edison-orchestrator.md"
    agent = agent_dir / "edison-agent.md"
    validator = agent_dir / "edison-validator.md"

    assert orchestrator.exists(), "edison-orchestrator.md should be generated"
    assert agent.exists(), "edison-agent.md should be generated"
    assert validator.exists(), "edison-validator.md should be generated"

    # Check orchestrator has correct mode
    orchestrator_content = orchestrator.read_text(encoding="utf-8")
    assert "mode: primary" in orchestrator_content

    # Check validator has restricted tools
    validator_content = validator.read_text(encoding="utf-8")
    assert "write: false" in validator_content or "edit: false" in validator_content


def test_opencode_setup_generates_command_files(isolated_project_env: Path) -> None:
    """Setup should generate Edison command markdown files under .opencode/command/."""
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--yes", "--commands")
    rc = main(args)
    assert rc == 0

    cmd_dir = isolated_project_env / ".opencode" / "command"
    assert cmd_dir.exists()

    # Check expected command files exist
    session_next = cmd_dir / "edison-session-next.md"
    session_status = cmd_dir / "edison-session-status.md"
    task_claim = cmd_dir / "edison-task-claim.md"

    assert session_next.exists(), "edison-session-next.md should be generated"
    assert session_status.exists(), "edison-session-status.md should be generated"
    assert task_claim.exists(), "edison-task-claim.md should be generated"

    # Check command content calls edison CLI
    next_content = session_next.read_text(encoding="utf-8")
    assert "edison session next" in next_content


def test_opencode_setup_all_flag_generates_everything(isolated_project_env: Path) -> None:
    """Setup with --all should generate plugin, agents, and commands."""
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--yes", "--all")
    rc = main(args)
    assert rc == 0

    # Plugin should exist
    plugin = isolated_project_env / ".opencode" / "plugin" / "edison.ts"
    assert plugin.exists()

    # Agents should exist
    agent_dir = isolated_project_env / ".opencode" / "agent"
    assert (agent_dir / "edison-orchestrator.md").exists()

    # Commands should exist
    cmd_dir = isolated_project_env / ".opencode" / "command"
    assert (cmd_dir / "edison-session-next.md").exists()


def test_opencode_agent_templates_have_valid_frontmatter(isolated_project_env: Path) -> None:
    """Generated agent files should have valid YAML frontmatter."""
    from edison.cli.opencode.setup import main
    import re

    args = _parse_setup_args(isolated_project_env, "--yes", "--agents")
    rc = main(args)
    assert rc == 0

    agent_file = isolated_project_env / ".opencode" / "agent" / "edison-orchestrator.md"
    content = agent_file.read_text(encoding="utf-8")

    # Check frontmatter structure
    assert content.startswith("---")
    frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert frontmatter_match, "Should have valid frontmatter delimiters"

    frontmatter = frontmatter_match.group(1)
    assert "description:" in frontmatter
    assert "mode:" in frontmatter
