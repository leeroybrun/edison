from __future__ import annotations
from helpers.io_utils import write_config

import os
from pathlib import Path

from edison.core.config.cache import clear_all_caches
from edison.core.utils.paths.records import RecordPaths

def _use_root(tmp_path: Path) -> None:
    os.environ["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    clear_all_caches()

def test_record_paths_resolve_from_yaml(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        """
        session:
          paths:
            root: .project/custom-sessions
          validation:
            maxLength: 32
          states:
            active: wip
            done: done
        tasks:
          paths:
            root: .project/custom-tasks
            qaRoot: .project/custom-qa
            metaRoot: .project/custom-meta
            template: .project/custom-tasks/TEMPLATE.md
          defaults:
            ownerPrefix: "- Owner: "
        """,
    )
    _use_root(tmp_path)

    paths = RecordPaths(repo_root=tmp_path)

    assert paths.sessions_root() == (tmp_path / ".project" / "custom-sessions").resolve()
    assert paths.session_state_dir("active") == (tmp_path / ".project" / "custom-sessions" / "wip").resolve()
    assert paths.session_json_path("s1", state="done") == (tmp_path / ".project" / "custom-sessions" / "done" / "s1" / "session.json").resolve()

    assert paths.tasks_root() == (tmp_path / ".project" / "custom-tasks").resolve()
    assert paths.task_state_dir("todo") == (tmp_path / ".project" / "custom-tasks" / "todo").resolve()

    assert paths.qa_root() == (tmp_path / ".project" / "custom-qa").resolve()
    assert paths.qa_state_dir("waiting") == (tmp_path / ".project" / "custom-qa" / "waiting").resolve()

    assert paths.evidence_root("task-123") == (tmp_path / ".project" / "custom-qa" / "validation-reports" / "task-123").resolve()

