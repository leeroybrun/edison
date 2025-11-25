from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

import yaml

ROOT = Path(__file__).resolve().parents[4]
CORE_PATH = ROOT / ".edison" / "core"
from edison.core.adapters.claude import ClaudeAdapter  # type: ignore  # noqa: E402


def _write_yaml(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _seed_generated(repo_root: Path) -> Path:
    generated_root = repo_root / ".agents" / "_generated"
    (generated_root / "agents").mkdir(parents=True, exist_ok=True)

    (generated_root / "ORCHESTRATOR_GUIDE.md").write_text("Guide body", encoding="utf-8")
    (generated_root / "orchestrator-manifest.json").write_text("{}", encoding="utf-8")

    agent = generated_root / "agents" / "demo.md"
    agent.write_text("# demo\nAgent body", encoding="utf-8")

    return generated_root


def _command_def() -> Dict:
    return {
        "id": "demo",
        "domain": "general",
        "command": "/demo",
        "short_desc": "Demo command",
        "full_desc": "Full description",
        "cli": "demo run",
        "args": [{"name": "target", "description": "Target file", "required": True}],
        "when_to_use": "Use during demo",
        "related_commands": [],
    }


def test_claude_adapter_generates_all(tmp_path: Path) -> None:
    """Test complete Claude Code generation."""
    generated_root = _seed_generated(tmp_path)

    # Core definitions
    _write_yaml(tmp_path / ".edison/core/config/commands.yaml", {"commands": [_command_def()]})
    _write_yaml(
        tmp_path / ".edison/core/config/hooks.yaml",
        {
            "hooks": {
                "enabled": True,
                "platforms": ["claude"],
                "definitions": {
                    "demo-hook": {
                        "type": "PreToolUse",
                        "hook_type": "command",
                        "enabled": True,
                        "blocking": False,
                        "description": "Demo hook",
                        "template": "demo-hook.sh.template",
                        "config": {"message": "hello"},
                    }
                },
            }
        },
    )

    template_dir = tmp_path / ".edison" / "core" / "templates" / "hooks"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "demo-hook.sh.template").write_text('echo "{{ config.message }}"\n', encoding="utf-8")

    # Project overlays
    _write_yaml(
        tmp_path / ".agents/config/project.yml",
        {"project": {"name": "claude-full-test"}},
    )
    _write_yaml(
        tmp_path / ".agents/config/commands.yml",
        {
            "commands": {
                "enabled": True,
                "platforms": ["claude"],
                "output_dirs": {"claude": str(tmp_path / ".claude" / "commands")},
            }
        },
    )
    _write_yaml(
        tmp_path / ".agents/config/settings.yml",
        {"settings": {"claude": {"generate": True, "data": {"editor": "claude", "theme": "dark"}}}},
    )
    _write_yaml(
        tmp_path / ".agents/config/hooks.yml",
        {"hooks": {"enabled": True, "platforms": ["claude"], "output_dir": str(tmp_path / ".claude" / "hooks")}},
    )

    adapter = ClaudeAdapter(generated_root, repo_root=tmp_path)
    output_root = tmp_path / ".claude"
    adapter.write_outputs(output_root)

    # Orchestrator + agents
    assert (output_root / "CLAUDE.md").is_file()
    assert (output_root / "agents" / "demo.md").is_file()

    # Commands
    cmd_path = output_root / "commands" / "demo.md"
    assert cmd_path.is_file()
    assert "Demo command" in cmd_path.read_text(encoding="utf-8")

    # Hooks
    hook_path = output_root / "hooks" / "demo-hook.sh"
    assert hook_path.is_file()
    assert "hello" in hook_path.read_text(encoding="utf-8")

    # Settings
    settings_path = output_root / "settings.json"
    assert settings_path.is_file()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings.get("editor") == "claude"
    assert settings.get("theme") == "dark"

