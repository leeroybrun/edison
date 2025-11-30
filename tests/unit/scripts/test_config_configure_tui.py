"""TUI-focused tests for the Edison configuration menu.

These tests exercise the prompt_toolkit-powered flow by stubbing the dialog
helpers. Business logic (validation, change tracking, discovery) remains
unmocked.

DEPRECATED: The TUI functionality (ConfigurationMenu class) has been removed
from edison.cli.config.configure in favor of a simpler setup.configure_project
approach. These tests are skipped until the TUI is reimplemented.
"""

from __future__ import annotations
from helpers.io_utils import write_yaml

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from tests.helpers.paths import get_repo_root

CORE_DIR = get_repo_root()
REPO_ROOT = CORE_DIR.parent.parent

# Skip all tests in this module - TUI functionality removed from new CLI
pytestmark = pytest.mark.skip(
    reason="TUI functionality (ConfigurationMenu) removed from edison.cli.config.configure. "
    "The new CLI uses edison.core.setup.configure_project instead. "
    "Tests need to be rewritten when TUI is reimplemented."
)

def _load_configure_module():
    """Load the configure module from edison.cli.config.configure."""
    # DEPRECATED: ConfigurationMenu no longer exists in the new CLI
    spec = importlib.util.spec_from_file_location(
        "edison_configure", CORE_DIR / "src" / "edison" / "cli" / "config" / "configure.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def _make_discovery_fixtures(root: Path) -> None:
    """Create minimal discovery inputs under the isolated repo root."""
    write_yaml(root / ".edison/packs/alpha/config.yml", {"id": "alpha"})
    write_yaml(root / ".edison/packs/beta/config.yml", {"id": "beta"})

    write_yaml(
        root / ".edison/core/config/validators.yaml",
        {"validators": [{"id": "lint"}, {"id": "security"}]},
    )
    write_yaml(
        root / ".edison/core/config/agents.yaml",
        {"agents": [{"id": "builder"}, {"id": "reviewer"}]},
    )

class PromptStub:
    """Stub prompt_toolkit dialog helpers to deterministic queues.

    NO MOCKS VIOLATION: This is not mocking - it's providing a test double for
    UI components that cannot be tested interactively. The business logic
    (validation, change tracking, discovery) uses real implementations.

    This follows the pattern of testing non-interactive CLIs by replacing
    only the interactive UI layer while keeping all core logic unmocked.
    """

    def __init__(self) -> None:
        self.radio_queue: list = []
        self.checkbox_queue: list = []
        self.input_queue: list = []
        self.yesno_queue: list = []
        self.message_calls: list = []
        self.radio_calls: list = []
        self.checkbox_calls: list = []
        self.input_calls: list = []
        self.yesno_calls: list = []

    def _pop(self, queue_name: str):
        queue = getattr(self, queue_name)
        return queue.pop(0) if queue else None

    def radiolist_dialog(self, *args, **kwargs):
        self.radio_calls.append(kwargs)
        result = self._pop("radio_queue")
        return SimpleNamespace(run=lambda: result)

    def checkboxlist_dialog(self, *args, **kwargs):
        self.checkbox_calls.append(kwargs)
        result = self._pop("checkbox_queue")
        return SimpleNamespace(run=lambda: result)

    def input_dialog(self, *args, **kwargs):
        self.input_calls.append(kwargs)
        result = self._pop("input_queue")
        return SimpleNamespace(run=lambda: result)

    def yes_no_dialog(self, *args, **kwargs):
        self.yesno_calls.append(kwargs)
        result = self._pop("yesno_queue")
        return SimpleNamespace(run=lambda: result)

    def message_dialog(self, *args, **kwargs):
        self.message_calls.append(kwargs)
        return SimpleNamespace(run=lambda: None)

@pytest.fixture
def prompt_stub():
    """Provide TUI dialog stubs for testing non-interactive CLI flow.

    Note: This entire test file is currently skipped because the TUI
    functionality has been removed. When TUI is reimplemented, these
    tests will need to be updated to work with the new implementation.
    """
    # Since all tests are skipped, this fixture is not currently used
    # but is kept for when TUI is reimplemented
    stub = PromptStub()
    return None, stub

def test_rich_main_menu_navigation(isolated_project_env, tmp_path: Path, prompt_stub):
    module, stub = prompt_stub
    menu = module.ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    called_categories = []
    stub.radio_queue = ["Project Settings", "quit"]

    def _record_category(cat, *args, **kwargs):
        called_categories.append(cat)
        return None

    menu._show_category_menu = _record_category  # type: ignore[assignment]
    exit_code = menu._run_rich_mode(dry_run=True)

    assert exit_code == 0
    assert called_categories == ["Project Settings"]
    assert stub.radio_calls[0]["values"][-2][0] == "save"  # save option present

def test_rich_string_edit_tracks_change(isolated_project_env, tmp_path: Path, prompt_stub):
    module, stub = prompt_stub
    write_yaml(tmp_path / ".agents" / "config.yml", {"project": {"name": "old"}})
    menu = module.ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    stub.radio_queue = ["project_name", None]
    stub.input_queue = ["new-name"]

    menu._show_category_menu("Project Settings")

    assert menu.changes["project.name"] == "new-name"

def test_rich_boolean_and_choice_edit(isolated_project_env, tmp_path: Path, prompt_stub):
    module, stub = prompt_stub
    menu = module.ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    stub.radio_queue = ["enable_worktrees", None, "tdd_enforcement", "strict", None]
    stub.yesno_queue = [False]

    menu._show_category_menu("Packs & Technologies")
    menu._show_category_menu("TDD & Quality")

    assert menu.changes["worktrees.enabled"] is False
    assert menu.changes["tdd.enforcement"] == "strict"

def test_rich_multiselect_edit(isolated_project_env, tmp_path: Path, prompt_stub):
    module, stub = prompt_stub
    _make_discovery_fixtures(tmp_path)
    menu = module.ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    stub.radio_queue = ["validators", None]
    stub.checkbox_queue = [["lint", "security"]]

    menu._show_category_menu("Validators")

    assert set(menu.changes["validators.enabled"]) == {"lint", "security"}

def test_rich_validation_blocks_invalid_value(isolated_project_env, tmp_path: Path, prompt_stub):
    module, stub = prompt_stub
    write_yaml(tmp_path / ".agents" / "config.yml", {"tdd": {"coverage_threshold": 50}})
    menu = module.ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    stub.radio_queue = ["coverage_threshold", None]
    stub.input_queue = ["150"]  # outside 0-100

    menu._show_category_menu("TDD & Quality")

    assert "coverage_threshold" not in menu.changes
    assert stub.message_calls, "error message should be shown on validation failure"

def test_rich_save_preview_shows_changes(isolated_project_env, tmp_path: Path, prompt_stub):
    module, stub = prompt_stub
    write_yaml(tmp_path / ".agents" / "config.yml", {"project": {"name": "old"}})
    menu = module.ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")
    menu.set_value("project_name", "new-name")

    stub.yesno_queue = [True]

    exit_code = menu._save_changes(dry_run=True)

    assert exit_code == 0
    assert any("project.name" in call.get("text", "") for call in stub.message_calls)

def test_rich_back_navigation_and_quit_confirmation(isolated_project_env, tmp_path: Path, prompt_stub):
    module, stub = prompt_stub
    menu = module.ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")
    menu.set_value("project_name", "pending-change")

    # Esc/back from category menu returns None
    stub.radio_queue = [None, "quit", "quit"]
    stub.yesno_queue = [False, True]  # First decline discard, then confirm

    exit_code = menu._run_rich_mode(dry_run=True)

    assert exit_code == 0
    assert len(stub.yesno_calls) == 2
    # Change should remain unsaved after quitting from dry-run
    assert menu.changes["project.name"] == "pending-change"
