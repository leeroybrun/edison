from __future__ import annotations

from argparse import Namespace
from pathlib import Path

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


def test_compose_all_managed_files_adds_project_gitignore(tmp_path: Path) -> None:
    _setup_minimal_project(tmp_path)

    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("", encoding="utf-8")

    args = Namespace(
        project_root=str(tmp_path),
        agents=False,
        validators=False,
        guidelines=False,
        constitutions=False,
        start=False,
        cursor_rules=False,
        roots=False,
        schemas=False,
        documents=False,
        dry_run=False,
        json=True,
        claude=False,
        cursor=False,
        zen=False,
        coderabbit=False,
        all_adapters=False,
        no_adapters=False,
        atomic_generated=False,
        clean_generated=False,
        profile=False,
    )
    assert main(args) == 0

    content = gitignore.read_text(encoding="utf-8")
    assert ".project/" in content
    assert ".edison/_generated/" in content

