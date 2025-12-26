from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.session import ensure_session


@pytest.mark.session
def test_session_context_markdown_includes_constitution_pointers_and_loop_driver(
    isolated_project_env: Path,
) -> None:
    session_id = "sess-context-md-001"
    ensure_session(session_id, state="active")

    from edison.core.session.context_payload import (
        build_session_context_payload,
        format_session_context_markdown,
    )

    payload = build_session_context_payload(
        project_root=isolated_project_env,
        session_id=session_id,
    )
    markdown = format_session_context_markdown(payload)

    assert "## Edison Context" in markdown
    assert session_id in markdown
    assert ".edison/_generated/constitutions/AGENTS.md" in markdown
    assert f"edison session next {session_id}" in markdown

