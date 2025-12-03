from __future__ import annotations
from helpers.io_utils import write_yaml

import sys
from pathlib import Path
from typing import Dict, List

import yaml
import pytest

pytest.skip("Legacy command composition tests superseded by unified components", allow_module_level=True)

from tests.helpers.paths import get_repo_root

ROOT = get_repo_root()
from edison.core.adapters.components.commands import (  # type: ignore  # noqa: E402
    CommandArg,
    CommandDefinition,
    CommandComposer,
    ClaudeCommandAdapter,
    CursorCommandAdapter,
    CodexCommandAdapter,
)
from tests.helpers.dummy_adapter import DummyAdapter

def _sample_command_def(
    id: str,
    *,
    domain: str = "general",
    command: str = "/demo",
    short_desc: str = "Short description",
    full_desc: str = "Full description",
    cli: str = "demo --run",
    args: List[Dict] | None = None,
    when_to_use: str = "Use when demoing",
    related: List[str] | None = None,
) -> Dict:
    return {
        "id": id,
        "domain": domain,
        "command": command,
        "short_desc": short_desc,
        "full_desc": full_desc,
        "cli": cli,
        "args": args or [{"name": "target", "description": "Target file", "required": True}],
        "when_to_use": when_to_use,
        "related_commands": related or [],
    }

def test_command_definition_dataclass() -> None:
    """CommandDefinition stores values and defaults."""
    arg = CommandArg(name="path", description="File path")
    cmd = CommandDefinition(
        id="list-files",
        domain="fs",
        command="/ls",
        short_desc="List files",
        full_desc="List directory contents",
        cli="ls -la",
        args=[arg],
        when_to_use="Inspect a directory",
        related_commands=["open-file"],
    )

    assert cmd.id == "list-files"
    assert cmd.args[0].required is True
    assert cmd.related_commands == ["open-file"]

def test_load_core_definitions(tmp_path: Path) -> None:
    """Core commands are loaded from bundled edison.data (plus any project additions).
    
    Architecture: Core commands come from bundled data, project can ADD commands.
    """
    # Create a project-level command that will be added to bundled core
    project_cmd = _sample_command_def("project-cmd")
    write_yaml(
        tmp_path / ".edison/config/commands.yaml",
        {"commands": {"definitions": [project_cmd]}},
    )

    composer = CommandComposer(DummyAdapter(tmp_path).context)
    defs = composer.load_definitions()
    defs_by_id = {d.id: d for d in defs}

    # Should include bundled core commands
    assert len(defs) >= 1, "Should load bundled core commands"
    
    # Should also include our project command
    assert "project-cmd" in defs_by_id, "Should include project commands"
    assert defs_by_id["project-cmd"].args[0].name == "target"

def test_merge_pack_definitions(tmp_path: Path) -> None:
    """Pack command definitions extend bundled commands and can be overridden by project.

    Architecture precedence: project > pack > core
    This test verifies that packs can override bundled core commands.
    """
    # Use a bundled command (session-next) and override it at pack level
    pack_override = _sample_command_def("session-next", short_desc="pack desc", args=[{"name": "a2", "description": "pack"}])
    pack_only = _sample_command_def("pack-only", domain="pack", short_desc="from pack")

    write_yaml(
        tmp_path / ".edison/packs/pack1/config/commands.yml",
        {"commands": {"definitions": [pack_override, pack_only]}},
    )
    # Write packs.active config so PacksConfig can read it
    write_yaml(tmp_path / ".edison/config/edison.yaml", {"packs": {"active": ["pack1"]}})

    config = {"commands": {}}
    composer = CommandComposer(DummyAdapter(tmp_path, config=config).context)
    defs = composer.load_definitions()
    defs_by_id = {d.id: d for d in defs}

    # Pack should override bundled core command
    assert defs_by_id["session-next"].short_desc == "pack desc"
    assert defs_by_id["session-next"].args[0].name == "a2"
    # Pack-only should be included
    assert "pack-only" in defs_by_id

def test_apply_project_overrides(tmp_path: Path) -> None:
    """Project .yml overrides take highest precedence over .yaml definitions.

    Layer order: bundled core → bundled packs → project packs → project.yaml → project.yml
    The test uses a unique command name to avoid conflicts with bundled commands.
    """
    # Define a unique command that doesn't exist in bundled data
    base_cmd = _sample_command_def("my-test-cmd", full_desc="yaml description")
    pack_override = _sample_command_def("my-test-cmd", full_desc="pack description")
    project_override = _sample_command_def("my-test-cmd", full_desc="project description", args=[{"name": "proj", "description": "proj arg"}])

    # Base definition in .yaml
    write_yaml(
        tmp_path / ".edison/config/commands.yaml",
        {"commands": {"definitions": [base_cmd]}},
    )
    # Pack override
    write_yaml(
        tmp_path / ".edison/packs/pack1/config/commands.yml",
        {"commands": {"definitions": [pack_override]}},
    )
    # Project override in .yml (highest priority)
    write_yaml(
        tmp_path / ".edison/config/commands.yml",
        {"commands": {"definitions": [project_override]}},
    )
    # Write packs.active config so PacksConfig can read it
    write_yaml(tmp_path / ".edison/config/edison.yaml", {"packs": {"active": ["pack1"]}})

    config = {"commands": {}}
    composer = CommandComposer(DummyAdapter(tmp_path, config=config).context)
    defs = composer.load_definitions()
    my_cmd = {d.id: d for d in defs}["my-test-cmd"]

    # .yml override should win
    assert my_cmd.full_desc == "project description"
    assert my_cmd.args[0].name == "proj"

def test_filter_by_domains(tmp_path: Path) -> None:
    """Domain selection filters commands."""
    defs = [
        CommandDefinition(
            id="cmd-a",
            domain="data",
            command="/a",
            short_desc="A",
            full_desc="A",
            cli="a",
            args=[],
            when_to_use="",
            related_commands=[],
        ),
        CommandDefinition(
            id="cmd-b",
            domain="infra",
            command="/b",
            short_desc="B",
            full_desc="B",
            cli="b",
            args=[],
            when_to_use="",
            related_commands=[],
        ),
    ]
    config = {"commands": {"selection": {"mode": "domains", "domains": ["data"]}}}
    composer = CommandComposer(DummyAdapter(tmp_path, config=config).context)

    filtered = composer.filter_definitions(defs)

    assert [d.id for d in filtered] == ["cmd-a"]

def test_filter_explicit(tmp_path: Path) -> None:
    """Explicit selection keeps only listed IDs."""
    defs = [
        CommandDefinition(
            id="cmd-a",
            domain="data",
            command="/a",
            short_desc="A",
            full_desc="A",
            cli="a",
            args=[],
            when_to_use="",
            related_commands=[],
        ),
        CommandDefinition(
            id="cmd-b",
            domain="infra",
            command="/b",
            short_desc="B",
            full_desc="B",
            cli="b",
            args=[],
            when_to_use="",
            related_commands=[],
        ),
    ]
    config = {"commands": {"selection": {"mode": "explicit", "ids": ["cmd-b"]}}}
    composer = CommandComposer(DummyAdapter(tmp_path, config=config).context)

    filtered = composer.filter_definitions(defs)

    assert [d.id for d in filtered] == ["cmd-b"]

def test_claude_adapter_render() -> None:
    """Claude adapter renders markdown with CLI and arguments."""
    cmd = CommandDefinition(
        id="demo",
        domain="general",
        command="/demo",
        short_desc="Run demo",
        full_desc="Run demo command",
        cli="demo run",
        args=[CommandArg(name="target", description="Target item")],
        when_to_use="When demoing",
        related_commands=[],
    )
    adapter = ClaudeCommandAdapter()

    rendered = adapter.render_command(cmd, {})

    assert "Claude" in rendered
    assert "/demo" in rendered
    assert "target" in rendered

def test_cursor_adapter_render() -> None:
    """Cursor adapter renders markdown."""
    cmd = CommandDefinition(
        id="demo",
        domain="general",
        command="/demo",
        short_desc="Run demo",
        full_desc="Run demo command",
        cli="demo run",
        args=[CommandArg(name="target", description="Target item")],
        when_to_use="When demoing",
        related_commands=[],
    )
    adapter = CursorCommandAdapter()

    rendered = adapter.render_command(cmd, {})

    assert "Cursor" in rendered
    assert "demo run" in rendered

def test_codex_adapter_render(tmp_path: Path) -> None:
    """Codex adapter renders markdown."""
    cmd = CommandDefinition(
        id="demo",
        domain="general",
        command="/demo",
        short_desc="Run demo",
        full_desc="Run demo command",
        cli="demo run",
        args=[CommandArg(name="target", description="Target item")],
        when_to_use="When demoing",
        related_commands=[],
    )
    adapter = CodexCommandAdapter()

    rendered = adapter.render_command(cmd, {})

    assert "Codex" in rendered
    assert "When demoing" in rendered

def test_compose_for_platform(tmp_path: Path) -> None:
    """compose_for_platform writes files to the platform directory."""
    config = {
        "commands": {
            "platforms": ["claude"],
            "output_dirs": {"claude": str(tmp_path / ".claude" / "commands")},
        }
    }
    composer = CommandComposer(DummyAdapter(tmp_path, config=config).context)
    defs = [
        CommandDefinition(
            id="demo",
            domain="general",
            command="/demo",
            short_desc="Run demo",
            full_desc="Run demo command",
            cli="demo run",
            args=[CommandArg(name="target", description="Target item")],
            when_to_use="When demoing",
            related_commands=[],
        )
    ]

    result = composer.compose_for_platform("claude", defs)

    assert "demo" in result
    out_path = result["demo"]
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "Run demo" in content

def test_compose_all_platforms(tmp_path: Path) -> None:
    """compose_all renders for every configured platform.
    
    The bundled core commands should be rendered for all platforms.
    """
    config = {
        "commands": {
            "platforms": ["claude", "cursor", "codex"],
            "output_dirs": {
                "claude": str(tmp_path / ".claude" / "commands"),
                "cursor": str(tmp_path / ".cursor" / "commands"),
                "codex": str(tmp_path / ".codex" / "prompts"),
            },
        }
    }
    composer = CommandComposer(DummyAdapter(tmp_path, config=config).context)

    result = composer.compose_all()

    assert set(result.keys()) == {"claude", "cursor", "codex"}
    # Each platform should have rendered bundled commands
    for platform, mapping in result.items():
        assert len(mapping) > 0, f"Should have rendered commands for {platform}"
        for cmd_id, path in mapping.items():
            assert path.exists(), f"Command file should exist for {cmd_id}"

def test_truncate_short_desc(tmp_path: Path) -> None:
    """Short descriptions are truncated to the configured maximum."""
    long_desc = "x" * 120
    cmd_def = _sample_command_def("long-cmd", short_desc=long_desc)
    write_yaml(tmp_path / ".edison/config/commands.yaml", {"commands": {"definitions": [cmd_def]}})

    composer = CommandComposer(DummyAdapter(tmp_path).context)
    defs = composer.load_definitions()
    
    # Find our specific command
    long_cmd = next((d for d in defs if d.id == "long-cmd"), None)
    assert long_cmd is not None, "Should find the long-cmd command"
    
    assert len(long_cmd.short_desc) <= 80
    assert long_cmd.short_desc.endswith("...")
