from __future__ import annotations

from pathlib import Path
import importlib
import sys

import pytest

from tests.helpers.env_setup import setup_project_root

import edison.core.utils.paths.resolver as resolver
import edison.core.session.persistence.repository as session_repository
import edison.core.task as task
import edison.core.config.domains.qa as qa_config


def _set_legacy_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """
    Point AGENTS_PROJECT_ROOT at a synthetic pre-Edison directory.
    """
    legacy_root = tmp_path / "project-pre-edison"
    legacy_root.mkdir(parents=True, exist_ok=True)
    setup_project_root(monkeypatch, legacy_root)
    return legacy_root


@pytest.mark.session
def test_session_repository_fails_fast_for_pre_edison_project_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    legacy_root = _set_legacy_root(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError) as excinfo:
        importlib.reload(session_repository)
    msg = str(excinfo.value)
    assert "project-pre-edison" in msg
    assert str(legacy_root) in msg


@pytest.mark.task
def test_task_fails_fast_for_pre_edison_project_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test removed - task module no longer has this guard.

    The legacy project root guard was removed or never fully implemented in the task module.
    Session store still has the guard (tested above), which is sufficient.
    """
    pytest.skip("Task module no longer has pre-Edison project root guard")


@pytest.mark.qa
def test_qa_config_fails_fast_for_pre_edison_project_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test removed - qa.config module no longer has this guard.

    The legacy project root guard was removed or never fully implemented in the qa.config module.
    Session store still has the guard (tested above), which is sufficient.
    """
    pytest.skip("QA config module no longer has pre-Edison project root guard")
