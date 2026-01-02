from __future__ import annotations

import shutil
from pathlib import Path

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.settings import SettingsComposer
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager
from edison.core.utils import resilience
from edison.core.utils.io import locking
from edison.core.utils.paths import project


class _AdapterStub:
    def get_active_packs(self) -> list[str]:
        return []


def _build_context(tmp_path: Path) -> AdapterContext:
    project_root = tmp_path
    project_dir = project_root / ".edison"
    user_dir = project_root / ".edison-user"
    core_dir = project_root / "core"
    bundled_packs_dir = project_root / "bundled_packs"
    user_packs_dir = user_dir / "packs"
    project_packs_dir = project_dir / "packs"

    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "config").mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "config").mkdir(exist_ok=True)
    bundled_packs_dir.mkdir(exist_ok=True)
    user_packs_dir.mkdir(parents=True, exist_ok=True)
    project_packs_dir.mkdir(parents=True, exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub()

    return AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        user_dir=user_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        user_packs_dir=user_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config={"hooks": {"enabled": False}, "settings": {"claude": {"preserve_custom": False}}},
        writer=writer,
        adapter=adapter_stub,
    )


def test_ide_settings_mkdir(tmp_path: Path) -> None:
    """SettingsComposer creates parent directory for settings.json."""
    composer = SettingsComposer(_build_context(tmp_path))

    target = tmp_path / ".claude" / "settings.json"
    assert not target.parent.exists()

    composer.write_settings_file()

    assert target.parent.exists()
    assert target.exists()


def test_locking_mkdir(tmp_path: Path) -> None:
    """acquire_file_lock creates parent directory."""
    target = tmp_path / "locks" / "myfile"
    assert not target.parent.exists()

    # fail_open=True to avoid waiting/locking issues in test
    with locking.acquire_file_lock(target, fail_open=True, nfs_safe=False):
        pass

    assert target.parent.exists()


def test_paths_project_mkdir(tmp_path: Path) -> None:
    """get_project_config_dir creates directory."""
    target = tmp_path / ".edison"
    if target.exists():
        shutil.rmtree(target)

    assert not target.exists()

    res = project.get_project_config_dir(tmp_path, create=True)

    assert res == target
    assert target.exists()


def test_resilience_mkdir(tmp_path: Path, monkeypatch) -> None:
    """resume_from_recovery creates active directory."""
    from tests.helpers.env_setup import setup_project_root
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    # Point Edison at the isolated tmp project root (SessionRepository + WorkflowConfig use it).
    # Using monkeypatch here keeps this test aligned with other suite patterns.
    setup_project_root(monkeypatch, tmp_path)

    sid = "sess-rec"
    repo = SessionRepository(project_root=tmp_path)
    repo.create(Session.create(sid, state="recovery"))

    rec_sess_dir = repo.get_session_json_path(sid).parent
    assert rec_sess_dir.exists()

    resumed_dir = resilience.resume_from_recovery(rec_sess_dir)

    assert resumed_dir.exists()
    assert (resumed_dir / "session.json").exists()
    assert not rec_sess_dir.exists()
