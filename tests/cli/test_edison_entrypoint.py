import os
import stat
import subprocess
from pathlib import Path

import importlib.util
from importlib.machinery import SourceFileLoader
import sys

ROOT = Path(__file__).resolve().parents[4]
EDISON_BIN = ROOT / "bin" / "edison"

loader = SourceFileLoader("edison_bin", str(EDISON_BIN))
spec = importlib.util.spec_from_loader("edison_bin", loader)
assert spec is not None
edison = importlib.util.module_from_spec(spec)
loader.exec_module(edison)


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IEXEC)


def test_detect_project_root_walks_up(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True, exist_ok=True)
    nested = root / "a" / "b"
    nested.mkdir(parents=True, exist_ok=True)
    assert edison.detect_project_root(nested) == root


def test_detect_edison_home_prefers_env(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / ".edison"
    (home / "core").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EDISON_HOME", str(home))
    assert edison.detect_edison_home() == home


def test_dispatch_executes_script(tmp_path: Path, monkeypatch) -> None:
    # Arrange Edison home with core/scripts/foo/bar
    edison_home = tmp_path / ".edison"
    scripts_dir = edison_home / "core" / "scripts" / "foo"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script = scripts_dir / "bar"
    script.write_text("#!/usr/bin/env python3\nprint('ran')\n", encoding="utf-8")
    _make_executable(script)

    project_root = tmp_path / "project"
    (project_root / ".git").mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(project_root)
    rc = edison.dispatch_command(edison_home, project_root, ["foo", "bar"])
    assert rc == 0


def test_setup_environment_sets_defaults(tmp_path: Path, monkeypatch) -> None:
    edison_home = tmp_path / ".edison"
    project_root = tmp_path / "project"
    (edison_home / "core").mkdir(parents=True, exist_ok=True)
    (project_root / ".git").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("EDISON_HOME", raising=False)
    monkeypatch.delenv("PROJECT_ROOT", raising=False)
    edison.setup_environment(edison_home, project_root)
    assert os.environ["EDISON_HOME"] == str(edison_home)
    assert os.environ["PROJECT_ROOT"] == str(project_root)
