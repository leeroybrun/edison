from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_session_create_json_prompt_path_only_by_default(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from edison.cli._dispatcher import main as cli_main

    code = cli_main(
        [
            "session",
            "create",
            "--session-id",
            "sess-prompt-001",
            "--no-worktree",
            "--prompt",
            "NEW_SESSION",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["startPromptId"] == "NEW_SESSION"
    assert data["startPromptPath"].endswith("START_NEW_SESSION.md")
    assert data["startPrompt"] is None


def test_session_create_json_prompt_includes_text_when_requested(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from edison.cli._dispatcher import main as cli_main

    code = cli_main(
        [
            "session",
            "create",
            "--session-id",
            "sess-prompt-002",
            "--no-worktree",
            "--prompt",
            "NEW_SESSION",
            "--include-prompt-text",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["startPromptId"] == "NEW_SESSION"
    assert data["startPromptPath"].endswith("START_NEW_SESSION.md")
    assert isinstance(data["startPrompt"], str) and data["startPrompt"].startswith("# START_NEW_SESSION")

