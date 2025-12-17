from __future__ import annotations

import json

from edison.cli._dispatcher import main as cli_main


def test_session_prompts_json_payload(isolated_project_env, capsys) -> None:
    rc = cli_main(["session", "prompts", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out or "{}")
    prompts = payload.get("prompts") or []
    assert "AUTO_NEXT" in prompts
