"""Integration tests for SettingsComposer (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.settings import SettingsComposer
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager


class _AdapterStub:
    def __init__(self, packs: list[str]) -> None:
        self._packs = packs

    def get_active_packs(self) -> list[str]:
        return self._packs


def _build_context(tmp_path: Path, config: dict) -> AdapterContext:
    project_root = tmp_path
    project_dir = project_root / ".edison"
    user_dir = project_root / ".edison-user"
    core_dir = project_root / "core"
    bundled_packs_dir = project_root / "bundled_packs"
    user_packs_dir = user_dir / "packs"
    project_packs_dir = project_dir / "packs"

    project_dir.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "config").mkdir(exist_ok=True)
    bundled_packs_dir.mkdir(exist_ok=True)
    user_packs_dir.mkdir(parents=True, exist_ok=True)
    project_packs_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "config").mkdir(exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub([])

    return AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        user_dir=user_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        user_packs_dir=user_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config=config,
        writer=writer,
        adapter=adapter_stub,
    )


def test_settings_composer_merges_core_and_project(tmp_path: Path) -> None:
    """Test that ConfigManager loads and merges project settings.

    ConfigManager loads:
    1. Bundled core settings (from edison.data/config/settings.yaml)
    2. Project settings (from .edison/config/settings.yaml)

    This test verifies project settings can override/extend bundled settings.
    """
    ctx = _build_context(
        tmp_path,
        config={
            "settings": {"claude": {"preserve_custom": False}},
            "hooks": {"enabled": False},
        },
    )

    # Write project settings that extend bundled defaults
    project_settings = ctx.project_dir / "config" / "settings.yaml"
    project_settings.write_text(
        """
settings:
  claude:
    env:
      PROJECT_CUSTOM: "test_value"
    permissions:
      allow: ["+", "custom_test_permission"]
""",
        encoding="utf-8",
    )

    composer = SettingsComposer(ctx)
    result = composer.compose()

    # Project settings should be merged with bundled defaults
    assert result["env"]["PROJECT_CUSTOM"] == "test_value"
    # Should have bundled permissions AND the appended one
    assert "custom_test_permission" in result["permissions"]["allow"]
    # Bundled permissions should still be present
    assert any("Read" in p for p in result["permissions"]["allow"])


def test_settings_composer_includes_core_tool_permissions(tmp_path: Path) -> None:
    """Core settings should allow essential Claude tools for Edison workflows."""
    ctx = _build_context(
        tmp_path,
        config={
            "settings": {"claude": {"preserve_custom": False}},
            "hooks": {"enabled": False},
        },
    )

    composer = SettingsComposer(ctx)
    result = composer.compose()

    allow = result.get("permissions", {}).get("allow") or []
    assert "Glob(./**)" in allow
    assert "Grep(./**)" in allow
    assert "Bash(edison:*)" in allow


def test_settings_composer_overwrites_hooks_when_preserving_custom_settings(tmp_path: Path) -> None:
    """Hooks are Edison-managed and should not be frozen by preserve_custom merges.

    In worktree-heavy setups, settings.json can be written from multiple worktrees.
    If we preserve an existing hooks section verbatim, it can embed worktree-specific
    absolute paths that later break when that worktree is archived.
    """
    ctx = _build_context(
        tmp_path,
        config={
            "settings": {"claude": {"preserve_custom": True, "backup_before": False}},
            # Allow hook generation (default is enabled; keep explicit for readability).
            "hooks": {"enabled": True},
        },
    )

    existing_settings_path = tmp_path / ".claude" / "settings.json"
    existing_settings_path.parent.mkdir(parents=True, exist_ok=True)
    existing_settings_path.write_text(
        """{
  "env": { "CUSTOM": "keep-me" },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "/tmp/bad-hook-path.sh" }
        ]
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    composer = SettingsComposer(ctx)
    written = composer.write_settings_file()
    assert written == existing_settings_path

    data = __import__("json").loads(written.read_text(encoding="utf-8"))
    assert data["env"]["CUSTOM"] == "keep-me"

    # Hooks should be replaced by the composed section, not preserved verbatim.
    hooks = data.get("hooks") or {}
    assert isinstance(hooks, dict)
    assert hooks, "Expected Edison to write a hooks section"
    # Sanity-check that at least one command hook uses the stable CLAUDE_PROJECT_DIR form.
    all_commands: list[str] = []
    for entries in hooks.values():
        for entry in entries:
            for hook in entry.get("hooks") or []:
                cmd = hook.get("command")
                if isinstance(cmd, str):
                    all_commands.append(cmd)
    assert any(cmd.startswith("$CLAUDE_PROJECT_DIR/") for cmd in all_commands)
