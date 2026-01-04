from __future__ import annotations

from pathlib import Path

import pytest


def test_detect_session_id_prefers_env_over_owner(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.paths.resolver import PathResolver

    repo = SessionRepository(project_root=isolated_project_env)
    repo.create(Session.create("env-session", owner="tester", state="active"))

    monkeypatch.setenv("AGENTS_SESSION", "env-session")
    assert PathResolver.detect_session_id(owner="someone") == "env-session"


def test_detect_session_id_infers_from_owner_active_session(
    isolated_project_env: Path,
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.paths.resolver import PathResolver

    repo = SessionRepository(project_root=isolated_project_env)
    repo.create(Session.create("sess-a", owner="tester", state="active"))
    repo.create(Session.create("sess-b", owner="other", state="active"))

    assert PathResolver.detect_session_id(owner="tester") == "sess-a"


def test_detect_session_id_returns_none_for_unknown_owner(
    isolated_project_env: Path,
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.paths.resolver import PathResolver

    repo = SessionRepository(project_root=isolated_project_env)
    repo.create(Session.create("sess-a", owner="tester", state="active"))

    assert PathResolver.detect_session_id(owner="nonexistent") is None


def test_detect_session_id_uses_session_id_file_when_present(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    # Note: .session-id is only consulted in linked worktrees (task 001-session-id-inference)
    # Mock is_worktree to simulate being inside a worktree
    from edison.core.utils.git import worktree as worktree_module
    from edison.core.utils.paths.resolver import PathResolver

    monkeypatch.setattr(worktree_module, "is_worktree", lambda path=None: True)

    repo = SessionRepository(project_root=isolated_project_env)
    repo.create(Session.create("sess-file-001", owner="tester", state="active"))

    session_id_file = isolated_project_env / ".project" / ".session-id"
    session_id_file.write_text("sess-file-001\n", encoding="utf-8")

    assert PathResolver.detect_session_id(owner="nonexistent") == "sess-file-001"


def test_detect_session_id_uses_configured_management_dir_for_session_file(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Session file lookup must follow configured management_dir, not hardcoded .project."""
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.paths.resolver import PathResolver

    # Ensure env doesn't mask file lookup.
    monkeypatch.delenv("AGENTS_SESSION", raising=False)

    # Note: .session-id is only consulted in linked worktrees (task 001-session-id-inference)
    # Mock is_worktree to simulate being inside a worktree
    from edison.core.utils.git import worktree as worktree_module

    monkeypatch.setattr(worktree_module, "is_worktree", lambda path=None: True)

    repo = SessionRepository(project_root=isolated_project_env)
    repo.create(Session.create("sess-file-003", owner="tester", state="active"))

    # Configure a custom management dir.
    edison_dir = isolated_project_env / ".edison"
    edison_dir.mkdir(exist_ok=True)
    (edison_dir / "config.yml").write_text("management_dir: .custom_mgmt\n", encoding="utf-8")

    session_id_file = isolated_project_env / ".custom_mgmt" / ".session-id"
    session_id_file.parent.mkdir(parents=True, exist_ok=True)
    session_id_file.write_text("sess-file-003\n", encoding="utf-8")

    assert PathResolver.detect_session_id(owner="nonexistent") == "sess-file-003"


def test_detect_session_id_prefers_env_over_session_id_file(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.paths.resolver import PathResolver

    repo = SessionRepository(project_root=isolated_project_env)
    repo.create(Session.create("env-session", owner="tester", state="active"))
    repo.create(Session.create("sess-file-002", owner="tester", state="active"))

    session_id_file = isolated_project_env / ".project" / ".session-id"
    session_id_file.write_text("sess-file-002\n", encoding="utf-8")

    monkeypatch.setenv("AGENTS_SESSION", "env-session")
    assert PathResolver.detect_session_id() == "env-session"


def test_detect_session_id_falls_back_to_process_derived_lookup(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.paths.resolver import PathResolver
    from edison.core.utils.process.inspector import find_topmost_process

    monkeypatch.delenv("AGENTS_SESSION", raising=False)
    monkeypatch.delenv("AGENTS_OWNER", raising=False)

    session_id_file = isolated_project_env / ".project" / ".session-id"
    session_id_file.unlink(missing_ok=True)

    name, pid = find_topmost_process()
    sid = f"{name}-pid-{pid}"

    repo = SessionRepository(project_root=isolated_project_env)
    repo.create(Session.create(sid, owner="tester", state="active"))

    assert PathResolver.detect_session_id() == sid
