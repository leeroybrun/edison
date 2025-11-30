from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pytest

from tests.helpers.paths import get_repo_root

ROOT = get_repo_root()
from edison.core.composition.ide.settings import SettingsComposer, merge_permissions  # type: ignore  # noqa: E402

from helpers.io_utils import write_yaml


def _core_settings(allow: list[str] | None = None) -> Dict:
    return {
        "settings": {
            "claude": {
                "backup_before": True,
                "permissions": {
                    "allow": allow or ["Read(./**)"],
                    "deny": [],
                    "ask": [],
                },
                "env": {"EDISON_ACTIVE": "true"},
                "enableAllProjectMcpServers": True,
            }
        }
    }


def test_load_core_settings(tmp_path: Path) -> None:
    """Core settings load from YAML and expose permissions/env."""
    write_yaml(tmp_path / ".edison/config/settings.yaml", _core_settings())

    composer = SettingsComposer(config={}, repo_root=tmp_path)
    settings = composer.load_core_settings()

    assert settings["permissions"]["allow"] == ["Read(./**)"]
    assert settings["env"]["EDISON_ACTIVE"] == "true"
    assert settings["enableAllProjectMcpServers"] is True


def test_extract_pack_permissions(tmp_path: Path) -> None:
    """Permissions from pack config are extracted."""
    pack_settings = {
        "settings": {"claude": {"permissions": {"allow": ["Bash(test:*)"], "deny": [], "ask": []}}}
    }
    write_yaml(tmp_path / ".edison/packs/pack1/config/settings.yml", pack_settings)
    write_yaml(tmp_path / ".edison/config/settings.yaml", _core_settings())

    composer = SettingsComposer(config={"packs": {"active": ["pack1"]}}, repo_root=tmp_path)
    perms = composer.extract_pack_permissions("pack1")

    assert perms["allow"] == ["Bash(test:*)"]
    assert perms["deny"] == []


def test_merge_permissions_arrays() -> None:
    """merge_permissions concatenates and de-duplicates per key."""
    base = {"allow": ["Read"], "deny": ["Secret"], "ask": []}
    overlay = {"allow": ["Write"], "deny": ["Secret"], "ask": ["Confirm"]}

    merged = merge_permissions(base, overlay)

    assert set(merged["allow"]) == {"Read", "Write"}
    assert set(merged["deny"]) == {"Secret"}
    assert merged["ask"] == ["Confirm"]


def test_merge_env_vars(tmp_path: Path) -> None:
    """Env dicts merge with overlay overriding duplicates."""
    write_yaml(tmp_path / ".edison/config/settings.yaml", _core_settings())
    composer = SettingsComposer(config={}, repo_root=tmp_path)

    base = {"env": {"A": "1", "B": "2"}}
    overlay = {"env": {"B": "override", "C": "3"}}

    merged = composer.deep_merge_settings(base, overlay)
    assert merged["env"] == {"A": "1", "B": "override", "C": "3"}


def test_compose_complete_settings(tmp_path: Path) -> None:
    """Core + pack + project overrides merge into final settings."""
    write_yaml(tmp_path / ".edison/config/settings.yaml", _core_settings())
    write_yaml(
        tmp_path / ".edison/packs/pack1/config/settings.yml",
        {"settings": {"claude": {"permissions": {"allow": ["PackAllow"], "deny": [], "ask": []}}}},
    )
    write_yaml(
        tmp_path / ".edison/config/settings.yml",
        {
            "settings": {
                "claude": {
                    "permissions": {"deny": ["ProjectDeny"]},
                    "env": {"PROJECT": "true"},
                }
            }
        },
    )

    config = {"packs": {"active": ["pack1"]}}
    composer = SettingsComposer(config=config, repo_root=tmp_path)
    result = composer.compose_settings()

    assert "PackAllow" in result["permissions"]["allow"]
    assert "ProjectDeny" in result["permissions"]["deny"]
    assert result["env"]["EDISON_ACTIVE"] == "true"
    assert result["env"]["PROJECT"] == "true"
    assert result["enableAllProjectMcpServers"] is True


def test_compose_with_hooks_section(tmp_path: Path) -> None:
    """HookComposer output is inserted when hooks are enabled.

    NO MOCKS: Uses real HookComposer with actual hook templates.
    """
    write_yaml(tmp_path / ".edison/config/settings.yaml", _core_settings())

    # Create a real hook definition that HookComposer can process
    hooks_config = {
        "hooks": {
            "definitions": {
                "test_hook": {
                    "type": "PreToolUse",
                    "hook_type": "command",
                    "enabled": True,
                    "description": "Test hook for settings composition",
                    "template": "test.sh.template",
                }
            }
        }
    }
    write_yaml(tmp_path / ".edison/config/hooks.yaml", hooks_config)

    # Create the hook template
    template_dir = tmp_path / ".edison" / "templates" / "hooks"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_file = template_dir / "test.sh.template"
    template_file.write_text("#!/usr/bin/env bash\n# {{ description }}\necho 'from hook'\n", encoding="utf-8")

    composer = SettingsComposer(config={"hooks": {"enabled": True}}, repo_root=tmp_path)
    settings = composer.compose_settings()

    # Verify hooks section was generated
    assert "hooks" in settings
    assert isinstance(settings["hooks"], dict)
    assert "PreToolUse" in settings["hooks"]
    assert isinstance(settings["hooks"]["PreToolUse"], list)
    assert len(settings["hooks"]["PreToolUse"]) > 0

    # Verify the hook entry structure
    hook_entry = settings["hooks"]["PreToolUse"][0]
    assert "matcher" in hook_entry
    assert "hooks" in hook_entry
    assert len(hook_entry["hooks"]) > 0
    assert hook_entry["hooks"][0]["type"] == "command"


def test_backup_existing_settings(tmp_path: Path) -> None:
    """Existing settings.json is backed up before overwrite when enabled."""
    write_yaml(tmp_path / ".edison/config/settings.yaml", _core_settings())
    target = tmp_path / ".claude/settings.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"old": True}), encoding="utf-8")

    composer = SettingsComposer(config={}, repo_root=tmp_path)
    written = composer.write_settings_file()

    backup = target.with_suffix(".json.bak")
    assert backup.exists()
    assert json.loads(backup.read_text(encoding="utf-8")) == {"old": True}

    new_data = json.loads(written.read_text(encoding="utf-8"))
    assert new_data["env"]["EDISON_ACTIVE"] == "true"
    assert written == target


def test_edison_internal_keys_stripped(tmp_path: Path) -> None:
    """Edison internal control flags are stripped from final output.

    Keys like 'enabled', 'generate', 'preserve_custom', 'backup_before', and
    'platforms' are Edison's internal control flags used during generation but
    should NOT appear in the final Claude Code settings.json.
    """
    # Core settings with internal control flags
    core_with_internal = {
        "settings": {
            "claude": {
                "enabled": True,  # Should be stripped
                "generate": True,  # Should be stripped
                "preserve_custom": True,  # Should be stripped
                "backup_before": True,  # Should be stripped
                "platforms": ["claude"],  # Should be stripped
                "permissions": {
                    "allow": ["Read(./**)"],
                    "deny": [],
                    "ask": [],
                },
                "env": {"EDISON_ACTIVE": "true"},
                "enableAllProjectMcpServers": True,  # Valid key - should remain
                "cleanupPeriodDays": 90,  # Valid key - should remain
            }
        }
    }
    write_yaml(tmp_path / ".edison/config/settings.yaml", core_with_internal)

    composer = SettingsComposer(config={}, repo_root=tmp_path)
    settings = composer.compose_settings()

    # Verify internal keys are stripped
    assert "enabled" not in settings
    assert "generate" not in settings
    assert "preserve_custom" not in settings
    assert "backup_before" not in settings
    assert "platforms" not in settings

    # Verify valid keys remain
    assert settings["permissions"]["allow"] == ["Read(./**)"]
    assert settings["env"]["EDISON_ACTIVE"] == "true"
    assert settings["enableAllProjectMcpServers"] is True
    assert settings["cleanupPeriodDays"] == 90
