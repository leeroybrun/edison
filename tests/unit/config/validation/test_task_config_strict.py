from __future__ import annotations
from helpers.io_utils import write_config

import os
from pathlib import Path

import pytest

from edison.core.config.cache import clear_all_caches
from edison.core.config.domains import TaskConfig

def _use_root(tmp_path: Path) -> None:
    os.environ["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    clear_all_caches()

def test_task_paths_require_yaml(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        """
        tasks:
          paths:
            root: ""
            qaRoot: ""
            metaRoot: ""
            template: ""
          defaults:
            ownerPrefix: "- Owner: "
        """,
    )
    _use_root(tmp_path)

    cfg = TaskConfig(repo_root=tmp_path)

    with pytest.raises(ValueError):
        cfg.tasks_root()

def test_task_paths_and_prefixes_from_yaml(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        """
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

    cfg = TaskConfig(repo_root=tmp_path)

    assert cfg.tasks_root() == (tmp_path / ".project" / "custom-tasks").resolve()
    assert cfg.qa_root() == (tmp_path / ".project" / "custom-qa").resolve()
    assert cfg.meta_root() == (tmp_path / ".project" / "custom-meta").resolve()
    assert cfg.template_path() == (tmp_path / ".project" / "custom-tasks" / "TEMPLATE.md").resolve()

    assert cfg.default_prefix("ownerPrefix") == "- Owner: "
