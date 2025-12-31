from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


def test_session_create_prompt_json_includes_start_prompt(
    isolated_project_env: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(
        yaml.safe_dump(
            {
                "worktrees": {
                    "enabled": True,
                    "baseBranchMode": "current",
                    "baseBranch": None,
                    "baseDirectory": str(tmp_path / "worktrees"),
                    "archiveDirectory": str(tmp_path / "worktrees" / "_archived"),
                    "branchPrefix": "session/",
                }
            }
        ),
        encoding="utf-8",
    )

    from edison.cli._dispatcher import main as cli_main

    code = cli_main(
        [
            "session",
            "create",
            "--session-id",
            "sess-start-prompt",
            "--owner",
            "tester",
            "--prompt",
            "AUTO_NEXT",
            "--include-prompt-text",
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out or "{}")
    assert payload.get("startPromptId") == "AUTO_NEXT"
    start_prompt = payload.get("startPrompt")
    assert isinstance(start_prompt, str)
    assert "# START_AUTO_NEXT" in start_prompt
