from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from tests.helpers.session import ensure_session


@pytest.mark.session
def test_session_context_cli_outputs_markdown(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    session_id = "sess-context-cli-001"
    ensure_session(session_id, state="active")

    from edison.cli.session.context import main as context_main

    args = argparse.Namespace(
        session_id=session_id,
        json=False,
        repo_root=isolated_project_env,
    )
    rc = context_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    assert "## Edison Context" in out
    assert session_id in out


@pytest.mark.session
def test_session_context_cli_can_append_memory_hits_when_enabled(
    isolated_project_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import os

    session_id = "sess-context-cli-memory-001"
    ensure_session(session_id, state="active")

    # Fake episodic-memory on PATH.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / "episodic-memory"
    fake.write_text("#!/usr/bin/env bash\necho \"FAKE_MEMORY_HIT\"\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | 0o111)
    monkeypatch.setenv("PATH", os.pathsep.join([str(bin_dir), os.environ.get("PATH", "")]))

    # Enable memory + context injection via project overrides.
    from tests.helpers.cache_utils import reset_edison_caches
    from tests.helpers.io_utils import write_yaml

    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "memory.yaml",
        {
            "memory": {
                "enabled": True,
                "defaults": {"maxHits": 2},
                "contextInjection": {
                    "enabled": True,
                    "limit": 1,
                    "queryTemplate": "{session_id}",
                    "heading": "## Memory Hits",
                    "maxCharsPerHit": 200,
                },
                "providers": {
                    "episodic": {
                        "kind": "external-cli-text",
                        "enabled": True,
                        "command": "episodic-memory",
                        "searchArgs": ["search", "{query}"],
                        "timeoutSeconds": 2,
                    }
                },
            }
        },
    )
    reset_edison_caches()

    from edison.cli.session.context import main as context_main

    args = argparse.Namespace(
        session_id=session_id,
        json=False,
        repo_root=isolated_project_env,
    )
    rc = context_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    assert "## Memory Hits" in out
    assert "FAKE_MEMORY_HIT" in out
