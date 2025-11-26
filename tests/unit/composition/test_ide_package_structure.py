"""Test that IDE-specific modules are properly organized in ide/ package.

This test validates the coherent organization of IDE-related composition modules:
- commands.py (IDE slash commands)
- hooks.py (IDE lifecycle hooks)
- settings.py (IDE settings.json)

These modules should be in edison.core.ide, NOT edison.core.composition.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_ide_package_exists() -> None:
    """The edison.core.ide package should exist."""
    try:
        import edison.core.ide
        assert edison.core.ide is not None
    except ImportError as e:
        raise AssertionError(f"edison.core.ide package should exist: {e}")


def test_ide_commands_module_exists() -> None:
    """IDE commands module should be in ide package."""
    try:
        from edison.core.ide import commands
        assert commands is not None
    except ImportError as e:
        raise AssertionError(f"edison.core.ide.commands should exist: {e}")


def test_ide_hooks_module_exists() -> None:
    """IDE hooks module should be in ide package."""
    try:
        from edison.core.ide import hooks
        assert hooks is not None
    except ImportError as e:
        raise AssertionError(f"edison.core.ide.hooks should exist: {e}")


def test_ide_settings_module_exists() -> None:
    """IDE settings module should be in ide package."""
    try:
        from edison.core.ide import settings
        assert settings is not None
    except ImportError as e:
        raise AssertionError(f"edison.core.ide.settings should exist: {e}")


def test_command_composer_in_ide() -> None:
    """CommandComposer should be importable from edison.core.ide.commands."""
    try:
        from edison.core.ide.commands import CommandComposer
        assert CommandComposer is not None
    except ImportError as e:
        raise AssertionError(f"CommandComposer should be in ide.commands: {e}")


def test_hook_composer_in_ide() -> None:
    """HookComposer should be importable from edison.core.ide.hooks."""
    try:
        from edison.core.ide.hooks import HookComposer
        assert HookComposer is not None
    except ImportError as e:
        raise AssertionError(f"HookComposer should be in ide.hooks: {e}")


def test_settings_composer_in_ide() -> None:
    """SettingsComposer should be importable from edison.core.ide.settings."""
    try:
        from edison.core.ide.settings import SettingsComposer
        assert SettingsComposer is not None
    except ImportError as e:
        raise AssertionError(f"SettingsComposer should be in ide.settings: {e}")


def test_ide_package_exports_all_composers() -> None:
    """IDE package __init__.py should export all composer classes."""
    try:
        from edison.core.ide import CommandComposer, HookComposer, SettingsComposer
        assert CommandComposer is not None
        assert HookComposer is not None
        assert SettingsComposer is not None
    except ImportError as e:
        raise AssertionError(f"IDE package should export all composers: {e}")


def test_composition_package_still_exports_ide_modules() -> None:
    """Composition package should re-export IDE modules for backward compatibility."""
    try:
        from edison.core.composition import CommandComposer, HookComposer, SettingsComposer
        assert CommandComposer is not None
        assert HookComposer is not None
        assert SettingsComposer is not None
    except ImportError as e:
        raise AssertionError(f"Composition should re-export IDE modules: {e}")


def test_no_ide_modules_in_composition_directory() -> None:
    """IDE modules should NOT exist as files in composition/ directory."""
    repo_root = Path(__file__).resolve().parents[3]
    composition_dir = repo_root / "src" / "edison" / "core" / "composition"

    # These files should NOT exist in composition/
    for filename in ["commands.py", "hooks.py", "settings.py"]:
        file_path = composition_dir / filename
        assert not file_path.exists(), f"{filename} should NOT exist in composition/ - it should be in ide/"


def test_ide_modules_exist_in_ide_directory() -> None:
    """IDE modules SHOULD exist as files in ide/ directory."""
    repo_root = Path(__file__).resolve().parents[3]
    ide_dir = repo_root / "src" / "edison" / "core" / "ide"

    # These files SHOULD exist in ide/
    for filename in ["__init__.py", "commands.py", "hooks.py", "settings.py"]:
        file_path = ide_dir / filename
        assert file_path.exists(), f"{filename} should exist in ide/"
