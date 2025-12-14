from __future__ import annotations

import argparse
from pathlib import Path

from edison.core.config.cache import clear_all_caches, is_cached


def test_task_list_register_args_does_not_load_config(isolated_project_env: Path) -> None:
    # Ensure a clean slate so this test is deterministic.
    clear_all_caches()

    from edison.cli.task import list as task_list

    parser = argparse.ArgumentParser()
    task_list.register_args(parser)

    # Building the CLI parser must not trigger config loads (performance).
    assert is_cached(repo_root=None, include_packs=True) is False


