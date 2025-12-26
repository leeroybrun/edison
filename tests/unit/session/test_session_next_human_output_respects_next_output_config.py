from __future__ import annotations

from pathlib import Path

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


def test_session_next_human_output_can_hide_recommendations_section(
    project_root: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(project_root)

    cfg_dir = project_root / ".edison" / "config"
    write_yaml(
        cfg_dir / "session.yaml",
        {"session": {"next": {"output": {"sections": {"recommendations": {"enabled": False}}}}}},
    )
    reset_edison_caches()

    from edison.core.session.next.output import format_human_readable

    payload = {
        "sessionId": "sess-xyz",
        "context": {"isEdisonProject": True, "projectRoot": str(project_root), "sessionId": "sess-xyz"},
        "actions": [],
        "blockers": [],
        "reportsMissing": [],
        "followUpsPlan": [],
        "rulesEngine": {},
        "rules": [],
        "recommendations": ["do the thing"],
    }

    text = format_human_readable(payload)
    assert "RECOMMENDATIONS" not in text
    assert "do the thing" not in text


def test_session_next_human_output_uses_configured_header_template(
    project_root: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(project_root)

    cfg_dir = project_root / ".edison" / "config"
    write_yaml(
        cfg_dir / "session.yaml",
        {"session": {"next": {"output": {"headerTemplate": "SESSION {sessionId} :: NEXT"}}}},
    )
    reset_edison_caches()

    from edison.core.session.next.output import format_human_readable

    payload = {
        "sessionId": "sess-abc",
        "context": {"isEdisonProject": True, "projectRoot": str(project_root), "sessionId": "sess-abc"},
        "actions": [],
        "blockers": [],
        "reportsMissing": [],
        "followUpsPlan": [],
        "rulesEngine": {},
        "rules": [],
        "recommendations": [],
    }

    text = format_human_readable(payload)
    assert "SESSION sess-abc :: NEXT" in text.splitlines()[0]

