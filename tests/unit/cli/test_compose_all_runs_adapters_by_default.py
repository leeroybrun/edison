from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from edison.cli.compose.all import main


def _setup_minimal_project(repo_root: Path) -> None:
    """Create minimal Edison project structure for compose-all tests."""
    # Minimal validators overlay so we get at least one predictable generated validator.
    validators_dir = repo_root / ".edison" / "validators"
    validators_dir.mkdir(parents=True, exist_ok=True)
    (validators_dir / "test-val.md").write_text(
        "# Test Validator\n\nValidator content.\n",
        encoding="utf-8",
    )

    config_dir = repo_root / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    # Minimal config; bundled defaults supply the rest.
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
    a.json = False
    a.claude = False
    a.cursor = False
    a.zen = False
    a.coderabbit = False
    a.all_adapters = False
    a.atomic_generated = False
    a.clean_generated = False
    a.profile = False
    return a


def test_compose_all_runs_enabled_adapters_by_default(tmp_path: Path, args: Namespace) -> None:
    """
    Full `edison compose all` should run enabled adapters by default.

    In particular, Zen sync should write agent + validator prompt files under `.zen/`.
    """
    _setup_minimal_project(tmp_path)
    args.project_root = str(tmp_path)

    assert main(args) == 0

    zen_project_dir = tmp_path / ".zen" / "conf" / "systemprompts" / "clink" / "project"
    assert zen_project_dir.exists(), f"Expected Zen project prompts dir: {zen_project_dir}"

    # Validator prompt (from project overlay) should be present.
    assert (zen_project_dir / "test-val.txt").exists()

    # Generic model prompts should be present and include the workflow loop.
    codex_prompt = zen_project_dir / "codex.txt"
    assert codex_prompt.exists()
    content = codex_prompt.read_text(encoding="utf-8")
    assert "## Edison Workflow Loop" in content
    assert "edison session next" in content
    assert "APPLICABLE RULES" in content
    assert "RECOMMENDED ACTIONS" in content
    assert "DELEGATION HINT" in content
    assert "VALIDATORS" in content
