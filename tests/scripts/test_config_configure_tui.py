"""TUI-focused tests for the Edison configuration menu.

These tests exercise the prompt_toolkit-powered flow by stubbing the dialog
helpers. Business logic (validation, change tracking, discovery) remains
unmocked.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
import yaml

import pytest

CORE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = CORE_DIR.parent.parent


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _load_configure_module():
    spec = importlib.util.spec_from_file_location(
        "edison_configure", CORE_DIR / "scripts" / "config" / "configure.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_discovery_fixtures(root: Path) -> None:
    """Create minimal discovery inputs under the isolated repo root."""
    _write_yaml(root / ".edison/packs/alpha/config.yml", {"id": "alpha"})
    _write_yaml(root / ".edison/packs/beta/config.yml", {"id": "beta"})

    _write_yaml(
        root / ".edison/core/config/validators.yaml",
        {"validators": [{"id": "lint"}, {"id": "security"}]},
    )
    _write_yaml(
        root / ".edison/core/config/agents.yaml",
        {"agents": [{"id": "builder"}, {"id": "reviewer"}]},
    )


class PromptStub:
    """Stub prompt_toolkit dialog helpers to deterministic queues."""

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
def prompt_stub(monkeypatch):
    """Patch prompt_toolkit dialog helpers with deterministic stubs."""
    stub = PromptStub()
    module = _load_configure_module()
    # Force rich path even when prompt_toolkit isn't installed.
    module.HAVE_PROMPT_TOOLKIT = True
    monkeypatch.setattr(module, "radiolist_dialog", stub.radiolist_dialog)
    monkeypatch.setattr(module, "checkboxlist_dialog", stub.checkboxlist_dialog)
    monkeypatch.setattr(module, "input_dialog", stub.input_dialog)
    monkeypatch.setattr(module, "yes_no_dialog", stub.yes_no_dialog)
    monkeypatch.setattr(module, "message_dialog", stub.message_dialog)
    return module, stub


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
    _write_yaml(tmp_path / ".agents" / "config.yml", {"project": {"name": "old"}})
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
    _write_yaml(tmp_path / ".agents" / "config.yml", {"tdd": {"coverage_threshold": 50}})
    menu = module.ConfigurationMenu(repo_root=tmp_path, edison_core=CORE_DIR, config_dir=".agents")

    stub.radio_queue = ["coverage_threshold", None]
    stub.input_queue = ["150"]  # outside 0-100

    menu._show_category_menu("TDD & Quality")

    assert "coverage_threshold" not in menu.changes
    assert stub.message_calls, "error message should be shown on validation failure"


def test_rich_save_preview_shows_changes(isolated_project_env, tmp_path: Path, prompt_stub):
    module, stub = prompt_stub
    _write_yaml(tmp_path / ".agents" / "config.yml", {"project": {"name": "old"}})
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
