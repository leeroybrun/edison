from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import yaml
import pytest

ROOT = Path(__file__).resolve().parents[4]
core_path = ROOT / ".edison" / "core"
from edison.core.ide.commands import (  # type: ignore  # noqa: E402
    CommandArg,
    CommandDefinition,
    CommandComposer,
    ClaudeCommandAdapter,
    CursorCommandAdapter,
    CodexCommandAdapter,
)


def _write_yaml(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


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
    """Core commands are loaded from .edison/core/config/commands.yaml."""
    core_cmd = _sample_command_def("core-cmd")
    _write_yaml(
        tmp_path / ".edison/core/config/commands.yaml",
        {"commands": {"definitions": [core_cmd]}},
    )

    composer = CommandComposer(config={"commands": {}}, repo_root=tmp_path)
    defs = composer.load_definitions()

    assert len(defs) == 1
    loaded = defs[0]
    assert loaded.id == "core-cmd"
    assert loaded.args[0].name == "target"


def test_merge_pack_definitions(tmp_path: Path) -> None:
    """Pack command definitions override and extend core definitions."""
    core_cmd = _sample_command_def("shared", short_desc="core desc", args=[{"name": "a1", "description": "core"}])
    pack_override = _sample_command_def("shared", short_desc="pack desc", args=[{"name": "a2", "description": "pack"}])
    pack_only = _sample_command_def("pack-only", domain="pack", short_desc="from pack")

    _write_yaml(
        tmp_path / ".edison/core/config/commands.yaml",
        {"commands": {"definitions": [core_cmd]}},
    )
    _write_yaml(
        tmp_path / ".edison/packs/pack1/config/commands.yml",
        {"commands": {"definitions": [pack_override, pack_only]}},
    )

    config = {"commands": {}, "packs": {"active": ["pack1"]}}
    composer = CommandComposer(config=config, repo_root=tmp_path)
    defs = composer.load_definitions()
    defs_by_id = {d.id: d for d in defs}

    assert defs_by_id["shared"].short_desc == "pack desc"
    assert defs_by_id["shared"].args[0].name == "a2"
    assert "pack-only" in defs_by_id


def test_apply_project_overrides(tmp_path: Path) -> None:
    """Project overrides in .agents/config/commands.yml take highest precedence."""
    core_cmd = _sample_command_def("shared", full_desc="core description")
    pack_override = _sample_command_def("shared", full_desc="pack description")
    project_override = _sample_command_def("shared", full_desc="project description", args=[{"name": "proj", "description": "proj arg"}])

    _write_yaml(
        tmp_path / ".edison/core/config/commands.yaml",
        {"commands": {"definitions": [core_cmd]}},
    )
    _write_yaml(
        tmp_path / ".edison/packs/pack1/config/commands.yml",
        {"commands": {"definitions": [pack_override]}},
    )
    _write_yaml(
        tmp_path / ".agents/config/commands.yml",
        {"commands": {"definitions": [project_override]}},
    )

    config = {"commands": {}, "packs": {"active": ["pack1"]}}
    composer = CommandComposer(config=config, repo_root=tmp_path)
    defs = composer.load_definitions()
    shared = {d.id: d for d in defs}["shared"]

    assert shared.full_desc == "project description"
    assert shared.args[0].name == "proj"


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
    composer = CommandComposer(config=config, repo_root=tmp_path)

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
    composer = CommandComposer(config=config, repo_root=tmp_path)

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
    composer = CommandComposer(config=config, repo_root=tmp_path)
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
    """compose_all renders for every configured platform."""
    core_cmd = _sample_command_def("demo")
    _write_yaml(
        tmp_path / ".edison/core/config/commands.yaml",
        {"commands": {"definitions": [core_cmd]}},
    )

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
    composer = CommandComposer(config=config, repo_root=tmp_path)

    result = composer.compose_all()

    assert set(result.keys()) == {"claude", "cursor", "codex"}
    for mapping in result.values():
        assert "demo" in mapping
        assert mapping["demo"].exists()


def test_truncate_short_desc(tmp_path: Path) -> None:
    """Short descriptions are truncated to the configured maximum."""
    long_desc = "x" * 120
    cmd_def = _sample_command_def("long", short_desc=long_desc)
    _write_yaml(tmp_path / ".edison/core/config/commands.yaml", {"commands": [cmd_def]})

    composer = CommandComposer(config={"commands": {}}, repo_root=tmp_path)
    defs = composer.load_definitions()
    short = defs[0].short_desc

    assert len(short) <= 80
    assert short.endswith("...")
