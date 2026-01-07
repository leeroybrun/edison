from __future__ import annotations

import os
from pathlib import Path

from edison.core.utils.locks import named_lock_path


def test_named_lock_path_global_scope_uses_user_config_dir(
    isolated_project_env: Path,
) -> None:
    user_root = Path(os.environ["EDISON_paths__user_config_dir"]).expanduser().resolve()

    p = named_lock_path(repo_root=isolated_project_env, namespace="web_server", key="k1", scope="global")

    assert p.resolve() == (user_root / "_locks" / "web_server" / "k1").resolve()


def test_named_lock_path_repo_scope_uses_project_config_dir(
    isolated_project_env: Path,
) -> None:
    p = named_lock_path(repo_root=isolated_project_env, namespace="web_server", key="k1", scope="repo")

    assert p.resolve() == (isolated_project_env / ".edison" / "_locks" / "web_server" / "k1").resolve()


def test_named_lock_path_session_scope_uses_project_session_locks_dir(
    isolated_project_env: Path,
) -> None:
    p = named_lock_path(
        repo_root=isolated_project_env,
        namespace="web_server",
        key="k1",
        scope="session",
        session_id="happy-pid-123",
    )

    assert p.resolve() == (
        isolated_project_env / ".edison" / "session" / "happy-pid-123" / "_locks" / "web_server" / "k1"
    ).resolve()
