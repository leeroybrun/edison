from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pytest

from tests.helpers.paths import get_repo_root

ROOT = get_repo_root()
from edison.core.adapters.components.settings import SettingsComposer, merge_permissions  # type: ignore  # noqa: E402

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
    """Core settings load from YAML and expose permissions/env.

    After unification, load_all_settings() loads from bundled Edison core settings
    first, then merges project settings. This test verifies that bundled core
    permissions are present and project settings can override/add to them.
    """
    write_yaml(tmp_path / ".edison/config/settings.yaml", _core_settings())

    composer = SettingsComposer(config={}, repo_root=tmp_path)
    # Use load_all_settings() which loads from all layers (core → packs → project)
    settings = composer.load_all_settings()

    # Verify bundled core permissions are present (19 items from core settings.yaml)
    assert "Read(./**)" in settings["permissions"]["allow"]
    assert "Edit(./**)" in settings["permissions"]["allow"]
    assert "Write(./**)" in settings["permissions"]["allow"]
    assert "Bash(git:*)" in settings["permissions"]["allow"]
    assert "WebSearch" in settings["permissions"]["allow"]
    assert "WebFetch" in settings["permissions"]["allow"]

    # Verify the project settings added EDISON_ACTIVE (core doesn't set it)
    assert settings["env"]["EDISON_ACTIVE"] == "true"

    # Verify bundled core setting
    assert settings["enableAllProjectMcpServers"] is True


def test_extract_pack_permissions(tmp_path: Path) -> None:
    """extract_pack_permissions() returns empty dict for non-existent pack.

    NOTE: extract_pack_permissions() reads from bundled Edison packs (real installation),
    not from tmp_path. Since there are currently no bundled packs with settings.yaml,
    this test verifies the method returns an empty dict gracefully.

    To test WITH pack permissions, we'd need to either:
    1. Create a real bundled pack with settings (not suitable for unit tests)
    2. Test against load_all_settings() which DOES support project packs (tested separately)
    """
    write_yaml(tmp_path / ".edison/config/settings.yaml", _core_settings())

    composer = SettingsComposer(config={"packs": {"active": ["nonexistent_pack"]}}, repo_root=tmp_path)
    perms = composer.extract_pack_permissions("nonexistent_pack")

    # Should return empty dict for non-existent pack
    assert perms == {}
    assert perms.get("allow") is None
    assert perms.get("deny") is None


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
    """Core + pack + project overrides merge into final settings.

    After unification, the compose flow is:
    1. Bundled Edison core settings (19 permissions from core settings.yaml)
    2. Project pack settings (PackAllow permission from .edison/packs/pack1)
    3. Project settings (ProjectDeny, PROJECT env from .edison/config/settings.yml)

    All permissions should be merged together. This test uses PROJECT packs
    (not bundled packs) since load_all_settings() supports project packs.

    NOTE: PacksConfig loads active packs from .edison/config/packs.yaml,
    so we must create that file in addition to passing config to composer.

    NOTE: load_all_settings() checks for settings.yaml first, then settings.yml.
    We must write project-level overrides to settings.yaml (not settings.yml) to ensure
    they're loaded as the project layer.
    """
    # Configure active packs via packs.yaml (PacksConfig reads from here)
    write_yaml(tmp_path / ".edison/config/packs.yaml", {"packs": {"active": ["pack1"]}})

    # Create pack in PROJECT location (.edison/packs/pack1)
    # load_all_settings() loads from project_packs_dir after bundled packs
    project_pack_dir = tmp_path / ".edison" / "packs" / "pack1" / "config"
    project_pack_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        project_pack_dir / "settings.yml",
        {"settings": {"claude": {"permissions": {"allow": ["PackAllow"], "deny": [], "ask": []}}}},
    )

    # Project-level settings override (must be settings.yaml, not settings.yml)
    write_yaml(
        tmp_path / ".edison/config/settings.yaml",
        {
            "settings": {
                "claude": {
                    "permissions": {"deny": ["ProjectDeny"]},
                    "env": {"PROJECT": "true", "EDISON_ACTIVE": "true"},
                }
            }
        },
    )

    config = {"packs": {"active": ["pack1"]}}
    composer = SettingsComposer(config=config, repo_root=tmp_path)
    result = composer.compose_settings()

    # Verify bundled core permissions are present
    assert "Read(./**)" in result["permissions"]["allow"]
    assert "Edit(./**)" in result["permissions"]["allow"]

    # Verify pack permission was merged from PROJECT pack
    assert "PackAllow" in result["permissions"]["allow"]

    # Verify project deny was merged (along with core denies)
    assert "ProjectDeny" in result["permissions"]["deny"]

    # Verify env vars merged from all layers
    assert result["env"]["EDISON_ACTIVE"] == "true"
    assert result["env"]["PROJECT"] == "true"

    # Verify core setting
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

    After unification, bundled core settings are loaded first, so we verify
    that internal keys are stripped from the final composed output.
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
    # After unification, bundled core settings are loaded first with 19 permissions,
    # then project settings merge in. Verify both are present.
    assert "Read(./**)" in settings["permissions"]["allow"]
    assert "Edit(./**)" in settings["permissions"]["allow"]  # From bundled core
    assert "Write(./**)" in settings["permissions"]["allow"]  # From bundled core

    assert settings["env"]["EDISON_ACTIVE"] == "true"
    assert settings["enableAllProjectMcpServers"] is True
    assert settings["cleanupPeriodDays"] == 90
