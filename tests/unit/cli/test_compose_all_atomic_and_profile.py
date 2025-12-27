from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from edison.cli.compose.all import main
from edison.core.utils.paths.project import get_project_config_dir


def _setup_minimal_edison_structure(repo_root: Path, validator_id: str = "test-val") -> None:
    """Create minimal Edison structure needed for composition tests."""
    validators_dir = repo_root / ".edison" / "validators"
    validators_dir.mkdir(parents=True, exist_ok=True)
    (validators_dir / f"{validator_id}.md").write_text(
        "# Test Validator\n"
        f"Test validator content for {validator_id}.\n"
        "Unique test guidance to avoid DRY violations.\n",
        encoding="utf-8",
    )

    # Minimal config overrides
    config_dir = repo_root / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yml").write_text(
        "packs:\n  active: []\n"
        "validation:\n  roster:\n    global: []\n    critical: []\n    specialized: []\n",
        encoding="utf-8",
    )


@pytest.fixture
def args() -> Namespace:
    a = Namespace()
    a.project_root = None
    a.agents = False
    a.validators = False
    a.constitutions = False
    a.guidelines = False
    a.start = False
    a.cursor_rules = False
    a.roots = False
    a.schemas = False
    a.documents = False
    a.dry_run = False
    a.json = False
    a.claude = False
    a.cursor = False
    a.pal = False
    a.coderabbit = False
    a.all_adapters = False
    # New flags (atomic + profiling); default off
    a.atomic_generated = False
    a.clean_generated = False
    a.profile = False
    return a


def test_compose_all_atomic_generated_removes_stale_files(tmp_path: Path, args: Namespace) -> None:
    _setup_minimal_edison_structure(tmp_path)
    args.project_root = str(tmp_path)

    # Initial compose creates _generated tree
    assert main(args) == 0

    config_dir = get_project_config_dir(tmp_path)
    generated_validators_dir = config_dir / "_generated" / "validators"
    generated_validators_dir.mkdir(parents=True, exist_ok=True)
    stale = generated_validators_dir / "stale.md"
    stale.write_text("stale", encoding="utf-8")
    assert stale.exists()

    # Atomic full rebuild should remove stale file
    args.atomic_generated = True
    assert main(args) == 0
    assert not stale.exists(), "Atomic rebuild should remove stale _generated files"


def test_compose_all_atomic_generated_works_when_generated_is_symlink(tmp_path: Path, args: Namespace) -> None:
    """Atomic compose must work when `<project-config-dir>/_generated` is a symlink.

    This models Edison worktree setups where session worktrees (and optionally primary)
    link `_generated` to a shared location.
    """
    _setup_minimal_edison_structure(tmp_path)
    args.project_root = str(tmp_path)

    config_dir = get_project_config_dir(tmp_path)
    generated = config_dir / "_generated"

    # Replace _generated with a symlink to a "shared" location.
    shared_root = tmp_path / "shared-generated-root"
    shared_root.mkdir(parents=True, exist_ok=True)
    shared_generated = shared_root / "_generated"
    shared_generated.mkdir(parents=True, exist_ok=True)

    if generated.exists():
        # In tests `_ensure_structure` may have created it as a real directory.
        import shutil

        shutil.rmtree(generated)

    generated.symlink_to(shared_generated, target_is_directory=True)
    assert generated.is_symlink()
    assert generated.resolve() == shared_generated.resolve()

    # Seed a stale file in the *target* directory.
    stale = shared_generated / "validators" / "stale.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("stale", encoding="utf-8")
    assert stale.exists()

    # Full compose (defaults to atomic rebuild) should succeed and remove stale files.
    assert main(args) == 0
    assert generated.is_symlink(), "Compose should not replace the symlink"
    assert not stale.exists(), "Atomic rebuild should remove stale files from symlink target"


def test_compose_all_profile_json_includes_profiling(tmp_path: Path, args: Namespace, capsys) -> None:
    _setup_minimal_edison_structure(tmp_path)
    args.project_root = str(tmp_path)
    args.json = True
    args.profile = True

    assert main(args) == 0

    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert "profiling" in data, "JSON output should include profiling when enabled"
    assert isinstance(data["profiling"], dict)
    assert "spans" in data["profiling"]
    assert isinstance(data["profiling"]["spans"], list)
    assert data["profiling"]["spans"], "Profiling spans should not be empty"


