from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path


def test_verify_session_health_requires_session_close_preset_bundle(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    from edison.core.qa.evidence import EvidenceService
    from edison.core.session.lifecycle import verify as verify_mod
    from edison.core.session.lifecycle.verify import verify_session_health

    monkeypatch.chdir(isolated_project_env)

    # Session-close preset is explicit (config-driven).
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "\n".join(
            [
                "validation:",
                "  sessionClose:",
                "    preset: deep",
                "  presets:",
                "    fast:",
                "      name: fast",
                "      validators: []",
                "      required_evidence: []",
                "      blocking_validators: []",
                "    deep:",
                "      name: deep",
                "      validators: []",
                "      required_evidence: []",
                "      blocking_validators: []",
                "",
            ]
        ),
        encoding="utf-8",
    )

    session_id = "python-pid-1"
    task_id = "900-wave1-session-close"

    # Create session-scoped task + QA records in done state.
    task_dir = isolated_project_env / ".project" / "sessions" / "wip" / session_id / "tasks" / "done"
    qa_dir = isolated_project_env / ".project" / "sessions" / "wip" / session_id / "qa" / "done"
    task_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    (task_dir / f"{task_id}.md").write_text(
        "\n".join(
            [
                "---",
                f"id: {task_id}",
                "title: Session close preset test",
                "owner: test",
                f"session_id: {session_id}",
                "---",
                "# Session close preset test",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (qa_dir / f"{task_id}-qa.md").write_text(
        "\n".join(
            [
                "---",
                f"id: {task_id}-qa",
                f"task_id: {task_id}",
                "title: QA",
                f"session_id: {session_id}",
                "---",
                "# QA",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Bundle summary is approved but uses the wrong preset, which must block session close.
    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)
    ev.write_bundle(
        {
            "taskId": task_id,
            "rootTask": task_id,
            "scope": "hierarchy",
            "preset": "fast",
            "round": 1,
            "approved": True,
            "tasks": [{"taskId": task_id, "approved": True}],
            "validators": [],
            "missing": [],
            "nonBlockingFollowUps": [],
        },
        round_num=1,
    )

    @contextmanager
    def _noop_in_session_worktree(_sid: str):
        yield

    monkeypatch.setattr(
        verify_mod.SessionContext,
        "in_session_worktree",
        staticmethod(_noop_in_session_worktree),
    )
    monkeypatch.setattr(verify_mod.session_manager, "get_session", lambda _sid: {"id": _sid})
    monkeypatch.setattr("edison.core.session.next.compute_next", lambda *_a, **_k: {"blockers": [], "reportsMissing": []})

    health = verify_session_health(session_id)

    assert health["ok"] is False
    assert health["categories"]["bundleWrongPreset"], "expected preset mismatch to block closing"
