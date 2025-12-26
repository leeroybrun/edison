from __future__ import annotations

import argparse
from pathlib import Path

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml
from tests.helpers.session import ensure_session


def test_memory_run_cli_executes_pipeline(isolated_project_env: Path, monkeypatch) -> None:
    monkeypatch.chdir(isolated_project_env)
    ensure_session("sess-1", state="active")

    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "memory.yaml",
        {
            "memory": {
                "enabled": True,
                "providers": {"file": {"kind": "file-store", "enabled": True}},
                "pipelines": {
                    "session-end": {
                        "enabled": True,
                        "steps": [
                            {"kind": "session-insights-v1", "outputVar": "insights"},
                            {
                                "kind": "provider-save-structured",
                                "provider": "file",
                                "inputVar": "insights",
                            },
                        ],
                    }
                },
            }
        },
    )
    reset_edison_caches()

    from edison.cli.memory.run import main

    rc = main(
        argparse.Namespace(
            event="session-end",
            session="sess-1",
            best_effort=False,
            json=True,
            repo_root=None,
        )
    )
    assert rc == 0

    path = isolated_project_env / ".project" / "memory" / "session_insights" / "sess-1.json"
    assert path.exists()

