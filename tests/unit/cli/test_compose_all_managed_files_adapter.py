from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from edison.cli.compose.all import main


def _setup_minimal_project(repo_root: Path) -> None:
    validators_dir = repo_root / ".edison" / "validators"
    validators_dir.mkdir(parents=True, exist_ok=True)
    (validators_dir / "test-val.md").write_text("# Test Validator\n", encoding="utf-8")

    config_dir = repo_root / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yml").write_text(
        "packs:\n  active: []\n"
        "validation:\n  roster:\n    global:\n      - id: test-val\n"
        "    critical: []\n"
        "    specialized: []\n",
        encoding="utf-8",
    )


@pytest.fixture
def args() -> Namespace:
    a = Namespace()
    a.project_root = None
    a.agents = False
    a.validators = False
    a.guidelines = False
    a.constitutions = False
    a.start = False
    a.cursor_rules = False
    a.roots = False
    a.schemas = False
    a.documents = False
    a.dry_run = False
    a.json = True
    a.claude = False
    a.cursor = False
    a.pal = False
    a.coderabbit = False
    a.all_adapters = False
    a.no_adapters = False
    a.atomic_generated = False
    a.clean_generated = False
    a.profile = False
    return a


def test_compose_all_json_includes_managed_files_sync(tmp_path: Path, args: Namespace, capsys) -> None:
    _setup_minimal_project(tmp_path)
    args.project_root = str(tmp_path)

    assert main(args) == 0

    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert "managed-files_sync" in data
    payload = data["managed-files_sync"]
    assert isinstance(payload, dict)
    assert "files" in payload

