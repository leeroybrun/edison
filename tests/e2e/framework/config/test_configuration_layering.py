"""Configuration layering and env override semantics (framework E2E).

Canonical config model (NO LEGACY):
- Core defaults live in bundled data: `edison.data/config/*.yaml`
- Project overlays live in: `<repo>/.edison/config/*.yml|*.yaml` (alphabetical merge)
- Environment overrides (EDISON_*) sit on top.

Key principles validated here:
- Precedence: env > project overlays > core defaults
- Env override paths are parsed fail-closed when validate=True
- Env override keys create canonical (lowercase) config keys
- YAML list merge supports append via the "+" sentinel (see edison.core.utils.merge.merge_arrays)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.config import ConfigManager
from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.io_utils import write_yaml


def _make_repo(tmp_path: Path) -> Path:
    repo = create_repo_with_git(tmp_path)
    (repo / ".edison" / "config").mkdir(parents=True, exist_ok=True)
    return repo


def test_precedence_env_over_project_over_core(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _make_repo(tmp_path)

    # Project overlay changes core default (core zen.retry.max_attempts=3)
    write_yaml(
        repo / ".edison" / "config" / "zen.yaml",
        {"zen": {"retry": {"max_attempts": 5}}},
    )

    # Env must win
    monkeypatch.setenv("EDISON_ZEN__RETRY__MAX_ATTEMPTS", "7")

    cfg = ConfigManager(repo_root=repo).load_config(validate=False)
    assert cfg["zen"]["retry"]["max_attempts"] == 7


def test_env_creates_new_keys_lowercased(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("EDISON_RUNTIME__LOG_LEVEL", "debug")

    cfg = ConfigManager(repo_root=repo).load_config(validate=False)
    assert cfg["runtime"]["log_level"] == "debug"


def test_env_array_index_and_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _make_repo(tmp_path)

    monkeypatch.setenv("EDISON_AGENTS__0", "codex")
    monkeypatch.setenv("EDISON_AGENTS__1", "claude")
    monkeypatch.setenv("EDISON_AGENTS__APPEND", "gemini")

    cfg = ConfigManager(repo_root=repo).load_config(validate=False)
    assert cfg["agents"] == ["codex", "claude", "gemini"]


def test_yaml_list_merge_append_plus_sentinel(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    # Alphabetical merge order: a.yaml then b.yaml.
    write_yaml(repo / ".edison" / "config" / "a.yaml", {"agents": ["codex"]})
    write_yaml(repo / ".edison" / "config" / "b.yaml", {"agents": ["+", "claude"]})

    cfg = ConfigManager(repo_root=repo).load_config(validate=False)
    assert cfg["agents"] == ["codex", "claude"]


def test_invalid_yaml_fails_closed(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    bad = repo / ".edison" / "config" / "bad.yaml"
    bad.write_text("this: [is: not: valid\n", encoding="utf-8")

    mgr = ConfigManager(repo_root=repo)
    with pytest.raises(Exception):
        _ = mgr.load_config(validate=False)


def test_malformed_env_override_fails_closed_when_validate_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _make_repo(tmp_path)

    # Empty segments are malformed in strict mode.
    monkeypatch.setenv("EDISON____BAD__PATH__", "oops")

    mgr = ConfigManager(repo_root=repo)
    with pytest.raises((ValueError, RuntimeError)):
        _ = mgr.load_config(validate=True)









