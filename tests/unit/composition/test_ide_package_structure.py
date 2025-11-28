"""Test that IDE-specific modules are properly organized in composition/ide/ subpackage.

This test validates the coherent organization of IDE-related composition modules:
- commands.py (IDE slash commands)
- hooks.py (IDE lifecycle hooks)
- settings.py (IDE settings.json)

These modules live in edison.core.composition.ide (NOT edison.core.ide).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_ide_package_exists() -> None:
    """The edison.core.composition.ide package should exist."""
    try:
        import edison.core.composition.ide
        assert edison.core.composition.ide is not None
    except ImportError as e:
        raise AssertionError(f"edison.core.composition.ide package should exist: {e}")


def test_ide_commands_module_exists() -> None:
    """IDE commands module should be in ide package."""
    try:
        from edison.core.composition.ide import commands
        assert commands is not None
    except ImportError as e:
        raise AssertionError(f"edison.core.ide.commands should exist: {e}")


def test_ide_hooks_module_exists() -> None:
    """IDE hooks module should be in ide package."""
    try:
        from edison.core.composition.ide import hooks
        assert hooks is not None
    except ImportError as e:
        raise AssertionError(f"edison.core.ide.hooks should exist: {e}")


def test_ide_settings_module_exists() -> None:
    """IDE settings module should be in ide package."""
    try:
        from edison.core.composition.ide import settings
        assert settings is not None
    except ImportError as e:
        raise AssertionError(f"edison.core.ide.settings should exist: {e}")


def test_command_composer_in_ide() -> None:
    """CommandComposer should be importable from edison.core.composition.ide.commands."""
    try:
        from edison.core.composition.ide.commands import CommandComposer
        assert CommandComposer is not None
    except ImportError as e:
        raise AssertionError(f"CommandComposer should be in ide.commands: {e}")


def test_hook_composer_in_ide() -> None:
    """HookComposer should be importable from edison.core.composition.ide.hooks."""
    try:
        from edison.core.composition.ide.hooks import HookComposer
        assert HookComposer is not None
    except ImportError as e:
        raise AssertionError(f"HookComposer should be in ide.hooks: {e}")


def test_settings_composer_in_ide() -> None:
    """SettingsComposer should be importable from edison.core.composition.ide.settings."""
    try:
        from edison.core.composition.ide.settings import SettingsComposer
        assert SettingsComposer is not None
    except ImportError as e:
        raise AssertionError(f"SettingsComposer should be in ide.settings: {e}")


def test_ide_package_exports_all_composers() -> None:
    """IDE package __init__.py should export all composer classes."""
    try:
        from edison.core.composition.ide import CommandComposer, HookComposer, SettingsComposer
        assert CommandComposer is not None
        assert HookComposer is not None
        assert SettingsComposer is not None
    except ImportError as e:
        raise AssertionError(f"IDE package should export all composers: {e}")


def test_ide_modules_also_exported_from_composition_root() -> None:
    """Composition package root re-exports IDE modules for convenience."""
    # IDE modules are available from both locations:
    # - edison.core.composition.ide (canonical location)
    # - edison.core.composition (convenience re-export)
    from edison.core.composition import CommandComposer, HookComposer, SettingsComposer
    assert CommandComposer is not None
    assert HookComposer is not None
    assert SettingsComposer is not None


def test_no_ide_modules_in_composition_root_directory() -> None:
    """IDE modules should NOT exist as files directly in composition/ root directory."""
    repo_root = Path(__file__).resolve().parents[3]
    composition_dir = repo_root / "src" / "edison" / "core" / "composition"

    # These files should NOT exist directly in composition/ (they should be in composition/ide/)
    for filename in ["commands.py", "hooks.py", "settings.py"]:
        file_path = composition_dir / filename
        assert not file_path.exists(), f"{filename} should NOT exist in composition/ root - it should be in composition/ide/"


def test_ide_modules_exist_in_composition_ide_directory() -> None:
    """IDE modules SHOULD exist as files in composition/ide/ directory."""
    repo_root = Path(__file__).resolve().parents[3]
    ide_dir = repo_root / "src" / "edison" / "core" / "composition" / "ide"

    # These files SHOULD exist in composition/ide/
    for filename in ["__init__.py", "commands.py", "hooks.py", "settings.py"]:
        file_path = ide_dir / filename
        assert file_path.exists(), f"{filename} should exist in composition/ide/"
