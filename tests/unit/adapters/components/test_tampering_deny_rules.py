"""TDD tests for tampering deny rules integration with settings composition.

Tests verify that when tampering protection is enabled:
1. A platform-agnostic DenyRules helper generates deny rules from TamperingConfig
2. SettingsComposer integrates deny rules into composed settings
3. Deny rules block write/edit access to protected directory
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.settings import SettingsComposer
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager


class _AdapterStub:
    """Minimal adapter stub for testing."""

    def __init__(self, packs: list[str]) -> None:
        self._packs = packs

    def get_active_packs(self) -> list[str]:
        return self._packs


def _build_context(tmp_path: Path, config: dict) -> AdapterContext:
    """Build a test adapter context."""
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


class TestDenyRulesFromTamperingConfig:
    """Tests for DenyRules generation from TamperingConfig."""

    def test_deny_rules_returns_empty_when_tampering_disabled(self, tmp_path: Path) -> None:
        """When tampering protection is disabled, deny rules should be empty."""
        from edison.core.adapters.components.tampering import DenyRules
        from edison.core.config.domains import TamperingConfig

        # Setup minimal Edison project structure
        (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

        # Create config with tampering disabled
        tampering_config_path = tmp_path / ".edison" / "config" / "tampering.yaml"
        tampering_config_path.write_text("tampering:\n  enabled: false\n")

        tampering_config = TamperingConfig(repo_root=tmp_path)
        deny_rules = DenyRules.from_tampering_config(tampering_config)

        assert deny_rules.deny_paths == []
        assert deny_rules.is_empty()

    def test_deny_rules_returns_protected_dir_when_enabled(self, tmp_path: Path) -> None:
        """When tampering protection is enabled, deny rules should include protected dir."""
        from edison.core.adapters.components.tampering import DenyRules
        from edison.core.config.domains import TamperingConfig

        (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

        # Create config with tampering enabled
        tampering_config_path = tmp_path / ".edison" / "config" / "tampering.yaml"
        tampering_config_path.write_text(
            "tampering:\n  enabled: true\n  protectedDir: .project/_protected\n"
        )

        tampering_config = TamperingConfig(repo_root=tmp_path)
        deny_rules = DenyRules.from_tampering_config(tampering_config)

        assert not deny_rules.is_empty()
        assert Path(".project/_protected") in deny_rules.deny_paths

    def test_deny_rules_uses_default_protected_dir(self, tmp_path: Path) -> None:
        """When no protectedDir specified, uses default _protected path."""
        from edison.core.adapters.components.tampering import DenyRules
        from edison.core.config.domains import TamperingConfig

        (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".project").mkdir(parents=True, exist_ok=True)

        tampering_config_path = tmp_path / ".edison" / "config" / "tampering.yaml"
        tampering_config_path.write_text("tampering:\n  enabled: true\n")

        tampering_config = TamperingConfig(repo_root=tmp_path)
        deny_rules = DenyRules.from_tampering_config(tampering_config)

        assert not deny_rules.is_empty()
        # Default is {management_root}/_protected
        assert any("_protected" in str(p) for p in deny_rules.deny_paths)


class TestDenyRulesPermissionGeneration:
    """Tests for permission string generation from DenyRules."""

    def test_deny_rules_generates_claude_permissions(self, tmp_path: Path) -> None:
        """DenyRules should generate Claude-compatible deny permission strings."""
        from edison.core.adapters.components.tampering import DenyRules

        deny_rules = DenyRules(deny_paths=[Path(".project/_protected")])
        permissions = deny_rules.to_claude_deny_permissions()

        # Should deny Read, Write, Edit to the protected path
        assert "Edit(./.project/_protected/**)" in permissions
        assert "Write(./.project/_protected/**)" in permissions

    def test_deny_rules_handles_multiple_paths(self, tmp_path: Path) -> None:
        """DenyRules should handle multiple protected paths."""
        from edison.core.adapters.components.tampering import DenyRules

        deny_rules = DenyRules(
            deny_paths=[
                Path(".project/_protected"),
                Path(".edison/secrets"),
            ]
        )
        permissions = deny_rules.to_claude_deny_permissions()

        assert "Edit(./.project/_protected/**)" in permissions
        assert "Write(./.project/_protected/**)" in permissions
        assert "Edit(./.edison/secrets/**)" in permissions
        assert "Write(./.edison/secrets/**)" in permissions


class TestSettingsComposerTamperingIntegration:
    """Tests for SettingsComposer integration with tampering deny rules."""

    def test_settings_composer_includes_tampering_deny_rules_when_enabled(
        self, tmp_path: Path
    ) -> None:
        """SettingsComposer should include deny rules when tampering is enabled."""
        ctx = _build_context(
            tmp_path,
            config={
                "settings": {"claude": {"preserve_custom": False}},
                "hooks": {"enabled": False},
            },
        )

        # Enable tampering protection
        tampering_config_path = ctx.project_dir / "config" / "tampering.yaml"
        tampering_config_path.write_text(
            "tampering:\n  enabled: true\n  protectedDir: .project/_protected\n"
        )

        composer = SettingsComposer(ctx)
        result = composer.compose()

        # Should have deny permissions for protected directory
        deny = result.get("permissions", {}).get("deny", [])
        assert any("_protected" in p for p in deny), f"Expected deny rules for _protected, got: {deny}"

    def test_settings_composer_excludes_tampering_deny_rules_when_disabled(
        self, tmp_path: Path
    ) -> None:
        """SettingsComposer should NOT include deny rules when tampering is disabled."""
        ctx = _build_context(
            tmp_path,
            config={
                "settings": {"claude": {"preserve_custom": False}},
                "hooks": {"enabled": False},
            },
        )

        # Disable tampering protection
        tampering_config_path = ctx.project_dir / "config" / "tampering.yaml"
        tampering_config_path.write_text("tampering:\n  enabled: false\n")

        composer = SettingsComposer(ctx)
        result = composer.compose()

        # Should NOT have deny permissions for protected directory
        deny = result.get("permissions", {}).get("deny", [])
        # Check that no _protected paths are in deny (unless they were there from core config)
        tampering_deny = [p for p in deny if "_protected" in p]
        assert len(tampering_deny) == 0, f"Unexpected tampering deny rules: {tampering_deny}"

    def test_settings_composer_merges_tampering_deny_with_existing(
        self, tmp_path: Path
    ) -> None:
        """SettingsComposer should merge tampering deny rules with existing deny rules."""
        ctx = _build_context(
            tmp_path,
            config={
                "settings": {"claude": {"preserve_custom": False}},
                "hooks": {"enabled": False},
            },
        )

        # Enable tampering protection
        tampering_config_path = ctx.project_dir / "config" / "tampering.yaml"
        tampering_config_path.write_text(
            "tampering:\n  enabled: true\n  protectedDir: .project/_protected\n"
        )

        composer = SettingsComposer(ctx)
        result = composer.compose()

        deny = result.get("permissions", {}).get("deny", [])

        # Should have BOTH core deny rules (like .env) AND tampering deny rules
        assert any(".env" in p for p in deny), "Missing core deny rules"
        assert any("_protected" in p for p in deny), "Missing tampering deny rules"
