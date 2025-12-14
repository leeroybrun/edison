from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import pytest

from edison.core.config.cache import clear_all_caches, is_cached


@pytest.mark.parametrize(
    "module_path",
    [
        "edison.cli.task.status",
        "edison.cli.task.claim",
        "edison.cli.qa.promote",
        "edison.cli.session.verify",
    ],
)
def test_register_args_does_not_load_config(isolated_project_env: Path, module_path: str) -> None:
    clear_all_caches()

    module = importlib.import_module(module_path)
    register_args = getattr(module, "register_args")

    parser = argparse.ArgumentParser()
    register_args(parser)

    assert is_cached(repo_root=None, include_packs=True) is False


