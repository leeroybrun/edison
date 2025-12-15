from __future__ import annotations

from pathlib import Path

import pytest


def test_require_session_id_errors_when_env_points_to_missing_session(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from edison.core.exceptions import SessionNotFoundError
    from edison.core.session.core.id import require_session_id

    monkeypatch.setenv("AGENTS_SESSION", "missing-session")

    with pytest.raises(SessionNotFoundError) as exc_info:
        require_session_id(project_root=isolated_project_env)

    assert "missing-session" in str(exc_info.value)


def test_require_session_id_errors_when_explicit_missing(
    isolated_project_env: Path,
) -> None:
    from edison.core.exceptions import SessionNotFoundError
    from edison.core.session.core.id import require_session_id

    with pytest.raises(SessionNotFoundError) as exc_info:
        require_session_id(explicit="missing-explicit", project_root=isolated_project_env)

    assert "missing-explicit" in str(exc_info.value)

