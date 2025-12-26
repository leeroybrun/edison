from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml
from tests.helpers.session import ensure_session


@pytest.mark.session
def test_session_context_markdown_respects_configured_fields(isolated_project_env: Path) -> None:
    session_id = "sess-context-cfg-001"
    ensure_session(session_id, state="active")

    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "session.yaml",
        {
            "session": {
                "context": {
                    "render": {
                        "markdown": {
                            # Only show project + session basics (no constitutions, no loop driver).
                            "fields": ["projectRoot", "session"],
                        }
                    }
                }
            }
        },
    )
    reset_edison_caches()

    from edison.core.session.context_payload import (
        build_session_context_payload,
        format_session_context_markdown,
    )

    payload = build_session_context_payload(project_root=isolated_project_env, session_id=session_id)
    markdown = format_session_context_markdown(payload)

    assert "## Edison Context" in markdown
    assert f"- Project:" in markdown
    assert session_id in markdown
    assert "Constitution (Agent)" not in markdown
    assert "Loop driver" not in markdown

