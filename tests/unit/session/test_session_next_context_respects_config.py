from __future__ import annotations

from pathlib import Path

from edison.core.config.domains.session import SessionConfig
from edison.core.session.core.models import Session
from edison.core.session.next.compute import compute_next
from edison.core.session.next.output import format_human_readable
from edison.core.session.persistence.repository import SessionRepository

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


def test_session_next_human_output_can_hide_context_block(project_root: Path, monkeypatch) -> None:
    monkeypatch.chdir(project_root)

    cfg_dir = project_root / ".edison" / "config"
    write_yaml(
        cfg_dir / "session.yaml",
        {"session": {"context": {"render": {"next": {"enabled": False}}}}},
    )
    reset_edison_caches()

    session_id = "sess-hide-context-001"
    repo = SessionRepository(project_root=project_root)
    initial_state = SessionConfig(repo_root=project_root).get_initial_session_state()
    repo.create(Session.create(session_id, owner="test", state=initial_state))

    payload = compute_next(session_id, scope=None, limit=5)
    out = format_human_readable(payload)

    assert "Edison Context:" not in out

