from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import pytest

from tests.helpers.timeouts import SHORT_SLEEP, THREAD_JOIN_TIMEOUT


@pytest.mark.qa
def test_evidence_capture_json_includes_lock_fields(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Minimal CI config for evidence capture.
    py = sys.executable.replace("\\", "\\\\")
    (isolated_project_env / ".edison" / "config" / "ci.yaml").write_text(
        f"ci:\n  commands:\n    test: \"{py} -c \\\"print('ok')\\\"\"\n",
        encoding="utf-8",
    )
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "210-wave1-evidence-capture-lock-json"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)
    EvidenceService(task_id=task_id, project_root=isolated_project_env).ensure_round(1)

    from edison.cli.evidence.capture import main as capture_main

    rc = capture_main(
        argparse.Namespace(
            task_id=task_id,
            only=["test"],
            all=False,
            preset=None,
            session_close=False,
            command_name=None,
            continue_on_failure=False,
            round_num=1,
            no_lock=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["commands"]
    cmd0 = payload["commands"][0]
    lock = cmd0.get("lock") or {}
    assert isinstance(lock.get("lockKey"), str) and lock.get("lockKey")
    assert isinstance(lock.get("lockPath"), str) and lock.get("lockPath")
    assert isinstance(lock.get("waitedMs"), int)
    assert lock.get("lockBypassed") is False


@pytest.mark.qa
def test_evidence_capture_resolves_short_task_id(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Minimal CI config for evidence capture.
    py = sys.executable.replace("\\", "\\\\")
    (isolated_project_env / ".edison" / "config" / "ci.yaml").write_text(
        f"ci:\n  commands:\n    test: \"{py} -c \\\"print('ok')\\\"\"\n",
        encoding="utf-8",
    )
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    full_id = "211-wave1-evidence-capture-short-id"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=full_id, title="Test", create_qa=False)
    EvidenceService(task_id=full_id, project_root=isolated_project_env).ensure_round(1)

    from edison.cli.evidence.capture import main as capture_main

    rc = capture_main(
        argparse.Namespace(
            task_id="211",
            only=["test"],
            all=False,
            preset=None,
            session_close=False,
            command_name=None,
            continue_on_failure=False,
            round_num=1,
            no_lock=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("taskId") == full_id


@pytest.mark.qa
def test_evidence_capture_lock_waits_for_existing_lock(
    isolated_project_env: Path,
) -> None:
    from edison.core.utils.locks.evidence_capture import acquire_evidence_capture_lock

    holder_ready = threading.Event()

    def _holder() -> None:
        with acquire_evidence_capture_lock(
            project_root=isolated_project_env,
            command_group="test",
            session_id="s1",
            timeout_seconds=5.0,
        ):
            holder_ready.set()
            time.sleep(SHORT_SLEEP * 6)

    t = threading.Thread(target=_holder, daemon=True)
    t.start()
    assert holder_ready.wait(timeout=THREAD_JOIN_TIMEOUT)

    start = time.monotonic()
    with acquire_evidence_capture_lock(
        project_root=isolated_project_env,
        command_group="test",
        session_id="s2",
        timeout_seconds=5.0,
    ) as info:
        elapsed = time.monotonic() - start
        # The second acquire should have waited for the holder to release.
        assert elapsed >= (SHORT_SLEEP * 4)
        assert str(info["lockPath"]).endswith(".project/qa/locks/evidence-capture-test.lock")

    t.join(timeout=THREAD_JOIN_TIMEOUT)
    assert not t.is_alive()
