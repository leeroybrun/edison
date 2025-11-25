from __future__ import annotations

from pathlib import Path
import importlib
import sys

import pytest

_CUR = Path(__file__).resolve()
ROOT: Path | None = None
CORE_ROOT: Path | None = None

for cand in _CUR.parents:
    if (cand / ".edison" / "core" / "lib" / "config.py").exists():
        ROOT = cand
        CORE_ROOT = cand / ".edison" / "core"
        break

assert ROOT is not None, "cannot locate Edison core root"
assert CORE_ROOT is not None
import edison.core.paths.resolver as resolver  # type: ignore
import edison.core.session.store as session_store  # type: ignore
import edison.core.task as task  # type: ignore
import edison.core.qa.config as qa_config  # type: ignore


def _set_legacy_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """
    Point AGENTS_PROJECT_ROOT at a synthetic pre-Edison directory.
    """
    legacy_root = tmp_path / "project-pre-edison"
    legacy_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(legacy_root))
    # Clear cached project root so guards re-resolve against the legacy path.
    resolver._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
    return legacy_root


@pytest.mark.session
def test_session_store_fails_fast_for_pre_edison_project_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    legacy_root = _set_legacy_root(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError) as excinfo:
        importlib.reload(session_store)
    msg = str(excinfo.value)
    assert "project-pre-edison" in msg
    assert str(legacy_root) in msg


@pytest.mark.task
def test_task_fails_fast_for_pre_edison_project_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    legacy_root = _set_legacy_root(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError) as excinfo:
        importlib.reload(task)
    msg = str(excinfo.value)
    assert "project-pre-edison" in msg
    assert str(legacy_root) in msg


@pytest.mark.qa
def test_qa_config_fails_fast_for_pre_edison_project_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    legacy_root = _set_legacy_root(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError) as excinfo:
        importlib.reload(qa_config)
    msg = str(excinfo.value)
    assert "project-pre-edison" in msg
    assert str(legacy_root) in msg
