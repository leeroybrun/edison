from __future__ import annotations

import json
import sys
from types import ModuleType
from pathlib import Path
from typing import Dict

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[4]
core_path = ROOT / ".edison" / "core"
from edison.core.composition.settings import SettingsComposer, merge_permissions  # type: ignore  # noqa: E402


def _write_yaml(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


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
    _write_yaml(tmp_path / ".edison/core/config/settings.yaml", _core_settings())

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
    _write_yaml(tmp_path / ".edison/packs/pack1/config/settings.yml", pack_settings)
    _write_yaml(tmp_path / ".edison/core/config/settings.yaml", _core_settings())

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
    _write_yaml(tmp_path / ".edison/core/config/settings.yaml", _core_settings())
    composer = SettingsComposer(config={}, repo_root=tmp_path)

    base = {"env": {"A": "1", "B": "2"}}
    overlay = {"env": {"B": "override", "C": "3"}}

    merged = composer.deep_merge_settings(base, overlay)
    assert merged["env"] == {"A": "1", "B": "override", "C": "3"}


def test_compose_complete_settings(tmp_path: Path) -> None:
    """Core + pack + project overrides merge into final settings."""
    _write_yaml(tmp_path / ".edison/core/config/settings.yaml", _core_settings())
    _write_yaml(
        tmp_path / ".edison/packs/pack1/config/settings.yml",
        {"settings": {"claude": {"permissions": {"allow": ["PackAllow"], "deny": [], "ask": []}}}},
    )
    _write_yaml(
        tmp_path / ".agents/config/settings.yml",
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


def test_compose_with_hooks_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """HookComposer output is inserted when hooks are enabled."""
    _write_yaml(tmp_path / ".edison/core/config/settings.yaml", _core_settings())

    module = ModuleType("lib.composition.hooks")

    class HookComposer:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def generate_settings_json_hooks_section(self) -> Dict:
            return {"PreToolUse": ["echo from hook"]}

    module.HookComposer = HookComposer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "lib.composition.hooks", module)

    composer = SettingsComposer(config={"hooks": {"enabled": True}}, repo_root=tmp_path)
    settings = composer.compose_settings()

    assert settings["hooks"] == {"PreToolUse": ["echo from hook"]}


def test_backup_existing_settings(tmp_path: Path) -> None:
    """Existing settings.json is backed up before overwrite when enabled."""
    _write_yaml(tmp_path / ".edison/core/config/settings.yaml", _core_settings())
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
