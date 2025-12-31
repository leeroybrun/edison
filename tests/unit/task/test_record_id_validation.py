from __future__ import annotations

import pytest
from pathlib import Path


def test_normalize_record_id_rejects_whitespace_in_id() -> None:
    from edison.core.task import normalize_record_id

    with pytest.raises(ValueError):
        normalize_record_id("task", "54-bad id")


def test_task_new_rejects_slug_with_spaces(
    isolated_project_env: Path,
) -> None:
    from edison.cli.task.new import main, register_args
    import argparse

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(
        [
            "--id",
            "54",
            "--slug",
            "bad slug",
            "--json",
            "--repo-root",
            str(isolated_project_env),
        ]
    )
    rc = main(args)
    assert rc != 0


def test_qa_new_rejects_task_id_with_spaces(
    isolated_project_env: Path,
) -> None:
    from edison.cli.qa.new import main, register_args
    import argparse

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(
        [
            "54-bad id",
            "--json",
            "--repo-root",
            str(isolated_project_env),
        ]
    )
    rc = main(args)
    assert rc != 0

