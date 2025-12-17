from __future__ import annotations

from pathlib import Path


def test_similarity_finds_matches_across_global_and_sessions(
    isolated_project_env: Path,
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.task.similarity import TaskSimilarityIndex

    # Create a real session (so session paths are discoverable via repository too)
    session_repo = SessionRepository(project_root=isolated_project_env)
    session_repo.create(Session.create("s1", owner="alice", state="wip"))

    task_repo = TaskRepository(project_root=isolated_project_env)
    task_repo.create(
        Task.create(
            "150-wave1-auth-gate",
            "Implement auth gate",
            description="Require authentication on protected routes",
            state="todo",
        )
    )
    task_repo.create(
        Task.create(
            "151-wave1-auth-middleware",
            "Add auth middleware",
            description="Implement middleware enforcing auth gate on routes",
            state="todo",
            session_id="s1",
        )
    )

    index = TaskSimilarityIndex.build(project_root=isolated_project_env)
    matches = index.search("auth gate", threshold=0.2, top_k=10)

    ids = {m.task_id for m in matches}
    assert "150-wave1-auth-gate" in ids
    assert "151-wave1-auth-middleware" in ids


def test_similarity_for_task_excludes_self(
    isolated_project_env: Path,
) -> None:
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.task.similarity import find_similar_tasks_for_task

    task_repo = TaskRepository(project_root=isolated_project_env)
    task_repo.create(
        Task.create(
            "200-wave1-fix-login",
            "Fix login bug",
            description="Handle refresh token expiry correctly",
            state="todo",
        )
    )
    task_repo.create(
        Task.create(
            "201-wave1-login-refresh",
            "Fix login refresh flow",
            description="Refresh token expiry handling",
            state="todo",
        )
    )

    matches = find_similar_tasks_for_task(
        "200-wave1-fix-login",
        project_root=isolated_project_env,
        threshold=0.2,
        top_k=10,
    )
    ids = {m.task_id for m in matches}
    assert "200-wave1-fix-login" not in ids
    assert "201-wave1-login-refresh" in ids

