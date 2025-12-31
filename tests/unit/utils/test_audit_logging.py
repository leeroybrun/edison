import json
import os
import sys
from pathlib import Path

from edison.cli._dispatcher import main as edison_main
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.io_utils import write_yaml


def _enable_logging(repo: Path) -> None:
    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        cfg_dir / "logging.yaml",
        {
            "logging": {
                "enabled": True,
                "audit": {
                    "enabled": True,
                    # Canonical audit log: a single append-only JSONL stream.
                    "path": ".project/logs/edison/audit.jsonl",
                },
                # Optional: embed small stdout/stderr tails into the canonical audit log
                # so consumers don't need to open per-invocation artifact files.
                "invocation": {"embed_tails": {"enabled": True, "max_bytes": 20000}},
                "stdlib": {
                    "enabled": True,
                    "level": "INFO",
                    "path": ".project/logs/edison/invocations/{invocation_id}.python.log",
                },
                "stdio": {
                    "capture": {
                        "enabled": True,
                        "paths": {
                            "stdout": ".project/logs/edison/invocations/{invocation_id}.stdout.log",
                            "stderr": ".project/logs/edison/invocations/{invocation_id}.stderr.log",
                        },
                    }
                },
                "subprocess": {
                    "enabled": True,
                    "max_output_bytes": 100000,
                },
            }
        },
    )


def test_subprocess_audit_log_written_when_enabled(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    _enable_logging(repo)
    # Enable redaction for this test
    write_yaml(
        repo / ".edison" / "config" / "logging-redaction.yaml",
        {"logging": {"redaction": {"enabled": True, "patterns": ["SECRET=[^\\n]+"]}}},
    )
    reset_edison_caches()

    cp = run_with_timeout(
        [sys.executable, "-c", "print('SECRET=hello')"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (cp.stdout or "").strip() == "SECRET=hello"

    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert log_path.exists()

    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    events = [json.loads(ln) for ln in lines]

    assert any(e.get("event") == "subprocess.end" for e in events)
    end = next(e for e in events if e.get("event") == "subprocess.end")
    assert end.get("returncode") == 0
    combined = (end.get("stdout") or "") + (end.get("stderr") or "")
    assert "SECRET=hello" not in combined
    assert "[REDACTED]" in combined


def test_cli_invocation_and_stdio_are_logged(tmp_path: Path, monkeypatch, capsys) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    _enable_logging(repo)
    reset_edison_caches()

    rc = edison_main(["config", "show", "project.name", "--format", "yaml", "--repo-root", str(repo)])
    assert rc == 0
    capsys.readouterr()

    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert log_path.exists()
    events = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    assert any(e.get("event") == "cli.invocation.start" for e in events)
    assert any(e.get("event") == "cli.invocation.end" for e in events)

    # Canonical log should embed stdout tail (when enabled) to avoid needing to open artifact files.
    end = next(e for e in reversed(events) if e.get("event") == "cli.invocation.end")
    assert "project:" in (end.get("stdout_tail") or "")

    inv_dir = repo / ".project" / "logs" / "edison" / "invocations"
    stdout_logs = sorted(inv_dir.glob("*.stdout.log"))
    stderr_logs = sorted(inv_dir.glob("*.stderr.log"))
    assert stdout_logs, "expected at least one stdout log file"
    assert stderr_logs, "expected at least one stderr log file"

    # Config show YAML output should include the key we requested.
    out = stdout_logs[-1].read_text(encoding="utf-8")
    assert "project:" in out


def test_stdlib_logging_is_written_to_per_invocation_file(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    _enable_logging(repo)
    reset_edison_caches()

    # We don't know the invocation_id here, so validate that stdlib logging config
    # can be used by tests by creating an invocation via the CLI.
    rc = edison_main(["config", "show", "project.name", "--format", "yaml", "--repo-root", str(repo)])
    assert rc == 0

    inv_dir = repo / ".project" / "logs" / "edison" / "invocations"
    py_logs = sorted(inv_dir.glob("*.python.log"))
    assert py_logs, "expected at least one stdlib python log file"

    import logging

    logger = logging.getLogger("edison.test")
    logger.info("hello-stdlib")

    content = py_logs[-1].read_text(encoding="utf-8")
    assert "hello-stdlib" in content


def test_configure_stdlib_logging_does_not_remove_existing_file_handlers(tmp_path: Path) -> None:
    """configure_stdlib_logging should only remove stdout/stderr stream handlers.

    Removing FileHandlers (which are also StreamHandlers) breaks any existing
    file-based logging in-process and can hide important debug traces.
    """
    import logging

    from edison.core.audit.stdlib_logging import (
        configure_stdlib_logging,
        reset_stdlib_logging_for_tests,
    )

    reset_stdlib_logging_for_tests()
    try:
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        external_log = tmp_path / "external.log"
        external_handler = logging.FileHandler(external_log, encoding="utf-8")
        root.addHandler(external_handler)

        edison_log = tmp_path / "edison.log"
        configure_stdlib_logging(log_path=edison_log, level="INFO")

        logging.getLogger("edison.test").info("hello-existing-filehandler")
        external_handler.flush()

        assert "hello-existing-filehandler" in external_log.read_text(encoding="utf-8")
    finally:
        reset_stdlib_logging_for_tests()


def test_audit_event_filters_hook_events_when_disabled(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    _enable_logging(repo)
    write_yaml(repo / ".edison" / "config" / "logging-hooks.yaml", {"logging": {"hooks": {"enabled": False}}})
    reset_edison_caches()

    from edison.core.audit.logger import audit_event

    audit_event("hook.test", repo_root=repo, hello="world")

    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert not log_path.exists()


def test_audit_event_filters_guard_events_when_disabled(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    _enable_logging(repo)
    write_yaml(repo / ".edison" / "config" / "logging-guards.yaml", {"logging": {"guards": {"enabled": False}}})
    reset_edison_caches()

    from edison.core.audit.logger import audit_event

    audit_event("guard.blocked", repo_root=repo, guard="x")

    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert not log_path.exists()


def test_cli_invocation_includes_session_id_when_agents_session_is_set(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    session_repo = SessionRepository(project_root=repo)
    session_repo.create(Session.create("sess-file-123", owner="tester", state="active"))

    monkeypatch.setenv("AGENTS_SESSION", "sess-file-123")

    _enable_logging(repo)
    reset_edison_caches()

    rc = edison_main(["config", "show", "project.name", "--format", "yaml", "--repo-root", str(repo)])
    assert rc == 0

    project_log = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert project_log.exists()
    events = [json.loads(ln) for ln in project_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    starts = [e for e in events if e.get("event") == "cli.invocation.start"]
    assert starts, "expected at least one cli.invocation.start event"
    assert starts[-1].get("session_id") == "sess-file-123"

    # Single canonical log: session-scoped logs should not be written as separate files.
    session_log = repo / ".project" / "logs" / "edison" / "audit-session-sess-file-123.jsonl"
    assert not session_log.exists()

    filtered = [e for e in events if e.get("session_id") == "sess-file-123"]
    assert any(e.get("event") == "cli.invocation.start" for e in filtered)


def test_cli_audit_invocation_uses_repo_root_argument_when_outside_project(tmp_path: Path) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    _enable_logging(repo)
    reset_edison_caches()

    # Run from outside the project without AGENTS_PROJECT_ROOT, relying on --repo-root.
    old_root = os.environ.pop("AGENTS_PROJECT_ROOT", None)
    old_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        rc = edison_main(["config", "show", "project.name", "--format", "yaml", "--repo-root", str(repo)])
        assert rc == 0
    finally:
        os.chdir(old_cwd)
        if old_root is not None:
            os.environ["AGENTS_PROJECT_ROOT"] = old_root

    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert log_path.exists()
    events = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert any(e.get("event") == "cli.invocation.start" for e in events)


def test_audit_jsonl_sink_disabled_produces_no_log_file(tmp_path: Path, monkeypatch) -> None:
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
                    "path": ".project/logs/edison/audit.jsonl",
                    "jsonl": {"enabled": False},
                },
            }
        },
    )
    reset_edison_caches()

    from edison.core.audit.logger import audit_event

    audit_event("hook.test", repo_root=repo, hello="world")

    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert not log_path.exists()


def test_cli_invocation_includes_task_id_when_task_arg_is_present(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    _enable_logging(repo)
    reset_edison_caches()

    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    task_repo = TaskRepository(project_root=repo)
    task_repo.create(Task.create("task-xyz", title="Audit task id test"))

    rc = edison_main(["qa", "new", "task-xyz", "--repo-root", str(repo)])
    assert rc == 0

    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert log_path.exists()
    events = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    starts = [e for e in events if e.get("event") == "cli.invocation.start"]
    assert starts, "expected at least one cli.invocation.start event"
    assert starts[-1].get("task_id") == "task-xyz"

    ends = [e for e in events if e.get("event") == "cli.invocation.end"]
    assert ends, "expected at least one cli.invocation.end event"
    assert ends[-1].get("task_id") == "task-xyz"


def test_legacy_audit_project_path_is_treated_as_canonical_path(tmp_path: Path, monkeypatch) -> None:
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
                            "paths": {
                                "project": ".project/logs/edison/audit.jsonl",
                                "session": ".project/logs/edison/audit-session-{session_id}.jsonl",
                            },
                        }
                    },
                },
            }
        },
    )
    reset_edison_caches()

    from edison.core.audit.logger import audit_event

    audit_event("hook.test", repo_root=repo, hello="world")

    # Canonical sink path should be honored even when configured via legacy keys.
    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    assert log_path.exists()
