from __future__ import annotations

import importlib.util
from pathlib import Path
import yaml


CORE_ROOT = Path(__file__).resolve().parents[2]
module_path = CORE_ROOT / "lib" / "paths" / "management.py"
spec = importlib.util.spec_from_file_location("lib.paths.management", module_path)
assert spec and spec.loader, "Unable to load lib.paths.management module spec"
management_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(management_module)  # type: ignore[arg-type]

ProjectManagementPaths = management_module.ProjectManagementPaths  # type: ignore[attr-defined]
get_management_paths = management_module.get_management_paths  # type: ignore[attr-defined]


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_defaults_to_dot_project(tmp_path: Path) -> None:
    paths = ProjectManagementPaths(tmp_path)
    assert paths.get_management_root() == tmp_path / ".project"
    assert paths.get_tasks_root() == tmp_path / ".project" / "tasks"
    assert paths.get_sessions_root() == tmp_path / ".project" / "sessions"
    assert paths.get_qa_root() == tmp_path / ".project" / "qa"
    assert paths.get_logs_root() == tmp_path / ".project" / "logs"
    assert paths.get_archive_root() == tmp_path / ".project" / "archive"


def test_custom_management_dir_from_config_yml(tmp_path: Path) -> None:
    cfg = tmp_path / ".agents" / "config.yml"
    _write_yaml(cfg, {"paths": {"management_dir": ".mgmt"}})

    paths = ProjectManagementPaths(tmp_path)
    assert paths.get_management_root() == tmp_path / ".mgmt"
    assert paths.get_tasks_root() == tmp_path / ".mgmt" / "tasks"
    assert paths.get_sessions_root() == tmp_path / ".mgmt" / "sessions"
    assert paths.get_qa_root() == tmp_path / ".mgmt" / "qa"
    assert paths.get_logs_root() == tmp_path / ".mgmt" / "logs"
    assert paths.get_archive_root() == tmp_path / ".mgmt" / "archive"


def test_config_paths_yaml_override(tmp_path: Path) -> None:
    cfg = tmp_path / ".agents" / "config" / "paths.yml"
    _write_yaml(cfg, {"project_management_dir": ".workspace"})

    paths = ProjectManagementPaths(tmp_path)
    assert paths.get_management_root() == tmp_path / ".workspace"


def test_task_and_session_state_dirs(tmp_path: Path) -> None:
    cfg = tmp_path / ".agents" / "config.yml"
    _write_yaml(cfg, {"project_management_dir": ".mgmt-dir"})

    paths = ProjectManagementPaths(tmp_path)
    assert paths.get_task_state_dir("todo") == tmp_path / ".mgmt-dir" / "tasks" / "todo"
    assert paths.get_task_state_dir("wip") == tmp_path / ".mgmt-dir" / "tasks" / "wip"
    assert paths.get_session_state_dir("active") == tmp_path / ".mgmt-dir" / "sessions" / "active"
    assert paths.get_session_state_dir("archived") == tmp_path / ".mgmt-dir" / "sessions" / "archived"


def test_global_get_management_paths_respects_repo_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".agents").mkdir(exist_ok=True)
    _write_yaml(tmp_path / ".agents" / "config.yml", {"paths": {"management_dir": ".control"}})

    paths = get_management_paths(repo_root=tmp_path)
    assert paths.get_management_root() == tmp_path / ".control"
