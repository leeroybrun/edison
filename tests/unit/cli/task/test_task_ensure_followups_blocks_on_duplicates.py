from __future__ import annotations

import argparse
from pathlib import Path

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.fixtures import create_task_file
from tests.helpers.io_utils import write_yaml


def test_task_ensure_followups_can_block_when_duplicate_check_configured(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Ensure a task exists whose title triggers followups.
    create_task_file(isolated_project_env, "800-api-change", state="todo", session_id=None, title="Add API endpoint")

    # Create an existing task matching the followup title ("Tests for ...").
    create_task_file(isolated_project_env, "801-existing", state="todo", session_id=None, title="Tests for 800-api-change")

    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "tasks.yaml",
        {"tasks": {"similarity": {"preCreate": {"enabled": True, "action": "block", "threshold": 0.1}}}},
    )
    reset_edison_caches()

    from edison.cli.task.ensure_followups import main

    rc = main(
        argparse.Namespace(
            task_id="800-api-change",
            session=None,
            dry_run=False,
            force=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 1

