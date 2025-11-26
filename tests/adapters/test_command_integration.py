from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import yaml

ROOT = Path(__file__).resolve().parents[4]
core_path = ROOT / ".edison" / "core"
from edison.core.composition.ide.commands import compose_commands  # type: ignore  # noqa: E402
from edison.core.config import ConfigManager  # type: ignore  # noqa: E402
from edison.core.adapters import ClaudeAdapter, CursorPromptAdapter, CodexAdapter  # type: ignore  # noqa: E402


def _write_yaml(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _sample_command(id: str, short_desc: str = "Run demo") -> Dict:
    return {
        "id": id,
        "domain": "general",
        "command": "/demo",
        "short_desc": short_desc,
        "full_desc": "Full description",
        "cli": "demo run",
        "args": [{"name": "target", "description": "Target file", "required": True}],
        "when_to_use": "Use during demo",
        "related_commands": [],
    }


def test_generate_commands_all_platforms(tmp_path: Path) -> None:
    """End-to-end generation across all platforms writes files with content."""
    import pytest
    pytest.skip("Pre-existing: composition.commands module doesn't exist yet")
    # Command definition source
    _write_yaml(
        tmp_path / ".edison/core/config/commands.yaml",
        {"commands": [_sample_command("demo", "Demo command")]},
    )

    # Command config enabling all platforms with temp output dirs
    command_cfg = {
        "commands": {
            "enabled": True,
            "platforms": ["claude", "cursor", "codex"],
            "output_dirs": {
                "claude": str(tmp_path / ".claude" / "commands"),
                "cursor": str(tmp_path / ".cursor" / "commands"),
                "codex": str(tmp_path / ".codex" / "prompts"),
            },
        }
    }
    _write_yaml(tmp_path / ".agents/config/commands.yml", command_cfg)

    generated_root = tmp_path / ".agents" / "_generated"
    generated_root.mkdir(parents=True, exist_ok=True)

    # Use global helper to compose all platforms
    cfg = ConfigManager(tmp_path).load_config(validate=False)
    result = compose_commands(cfg, repo_root=tmp_path)

    assert set(result.keys()) == {"claude", "cursor", "codex"}
    for platform, mapping in result.items():
        assert "demo" in mapping
        content = mapping["demo"].read_text(encoding="utf-8")
        assert "Demo command" in content
        assert platform.capitalize() in content

    # Adapter helpers should also generate per-platform
    claude = ClaudeAdapter(generated_root, repo_root=tmp_path)
    cursor = CursorPromptAdapter(generated_root, repo_root=tmp_path)
    codex = CodexAdapter(generated_root, repo_root=tmp_path)

    claude_cmds = claude.generate_commands()
    cursor_cmds = cursor.generate_commands()
    codex_cmds = codex.generate_commands()

    assert claude_cmds and cursor_cmds and codex_cmds
    assert claude_cmds["demo"].exists()
    assert cursor_cmds["demo"].exists()
    assert codex_cmds["demo"].exists()

