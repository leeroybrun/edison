import json
import sys
import time
from pathlib import Path

from edison.core.orchestrator.launcher import OrchestratorLauncher
from edison.core.config.domains import OrchestratorConfig

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.io_utils import write_yaml


def test_orchestrator_launch_emits_audit_events(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))

    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    write_yaml(
        cfg_dir / "logging.yaml",
        {
            "logging": {
                "enabled": True,
                "audit": {
                    "enabled": True,
                    "sinks": {
                        "jsonl": {
                            "enabled": True,
                            "paths": {"project": ".project/logs/edison/audit-project.jsonl"},
                        }
                    },
                },
            }
        },
    )

    write_yaml(
        cfg_dir / "orchestrator.yaml",
        {
            "orchestrators": {
                "default": "test",
                "profiles": {
                    "test": {
                        "command": sys.executable,
                        "args": ["-c", "print('hello-orch')"],
                        "cwd": "{project_root}",
                        "initial_prompt": {"enabled": False},
                    }
                },
            }
        },
    )

    reset_edison_caches()

    class _Ctx:
        session_id = "sess-test"
        session = {"id": "sess-test"}
        project_root = repo
        session_worktree = None
        worktree_path = None

    launcher = OrchestratorLauncher(OrchestratorConfig(repo, validate=False), _Ctx())
    proc = launcher.launch("test", detach=False)
    rc = proc.wait(timeout=5)
    assert rc == 0

    log_path = repo / ".project" / "logs" / "edison" / "audit-project.jsonl"
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    events = [json.loads(ln) for ln in lines]

    assert any(e.get("event") == "orchestrator.launch.start" for e in events)
    assert any(e.get("event") == "orchestrator.launch.end" for e in events)


def test_orchestrator_log_file_elides_prompt_when_capture_disabled(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))

    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    write_yaml(
        cfg_dir / "logging.yaml",
        {
            "logging": {
                "enabled": True,
                "audit": {
                    "enabled": True,
                    "sinks": {
                        "jsonl": {
                            "enabled": True,
                            "paths": {"project": ".project/logs/edison/audit-project.jsonl"},
                        }
                    },
                },
                "orchestrator": {"enabled": True, "capture_prompt": False},
            }
        },
    )

    write_yaml(
        cfg_dir / "orchestrator.yaml",
        {
            "orchestrators": {
                "default": "test",
                "profiles": {
                    "test": {
                        "command": sys.executable,
                        "args": ["-c", "print('hello-orch')"],
                        "cwd": "{project_root}",
                        "initial_prompt": {"enabled": False},
                    }
                },
            }
        },
    )

    reset_edison_caches()

    class _Ctx:
        session_id = "sess-test"
        session = {"id": "sess-test"}
        project_root = repo
        session_worktree = None
        worktree_path = None

    launcher = OrchestratorLauncher(OrchestratorConfig(repo, validate=False), _Ctx())
    log_path = repo / ".project" / "logs" / "edison" / "orchestrator-test.log"
    proc = launcher.launch("test", initial_prompt="TOPSECRET", log_path=log_path, detach=False)
    rc = proc.wait(timeout=5)
    assert rc == 0

    content = log_path.read_text(encoding="utf-8")
    assert "TOPSECRET" not in content
