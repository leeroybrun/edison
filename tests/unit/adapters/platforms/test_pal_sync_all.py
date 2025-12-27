"""End-to-end smoke for PalAdapter.sync_all (no mocks, minimal setup)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.platforms.pal import PalAdapter


def _setup_generated_agents(tmp_path: Path) -> None:
    gen_agents = tmp_path / ".edison" / "_generated" / "agents"
    gen_agents.mkdir(parents=True, exist_ok=True)
    (gen_agents / "alpha.md").write_text("# Alpha\nAlpha agent.\n", encoding="utf-8")
    (gen_agents / "api-builder.md").write_text("# API Builder\n", encoding="utf-8")

def _setup_generated_validators(tmp_path: Path) -> None:
    gen_validators = tmp_path / ".edison" / "_generated" / "validators"
    gen_validators.mkdir(parents=True, exist_ok=True)
    (gen_validators / "api.md").write_text("# Validator: api\n", encoding="utf-8")


def test_pal_sync_all_runs(tmp_path: Path) -> None:
    project_root = tmp_path

    _setup_generated_agents(project_root)
    _setup_generated_validators(project_root)

    # Seed legacy prompt filenames that must be removed by PalAdapter.sync_all.
    prompts_dir = project_root / ".pal" / "conf" / "systemprompts" / "clink" / "project"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "alpha.txt").write_text("legacy agent prompt", encoding="utf-8")
    (prompts_dir / "api-builder.txt").write_text("legacy agent prompt", encoding="utf-8")
    (prompts_dir / "api.txt").write_text("legacy validator prompt", encoding="utf-8")
    (prompts_dir / "codex_default.txt").write_text("legacy builtin prompt", encoding="utf-8")
    (prompts_dir / "claude_default.txt").write_text("legacy builtin prompt", encoding="utf-8")
    (prompts_dir / "gemini_default.txt").write_text("legacy builtin prompt", encoding="utf-8")

    adapter = PalAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Smoke: just assert structure and that Pal output directories exist.
    assert isinstance(result, dict)
    pal_conf = project_root / ".pal" / "conf"
    assert pal_conf.exists()
    # Pal needs CLI client configs (conf/cli_clients) to expose roles to clink.
    assert (pal_conf / "cli_clients").exists()
    # Builtin role prompts are shared across models (no model-specific duplication).
    prompts_dir = pal_conf / "systemprompts" / "clink" / "project"
    assert (prompts_dir / "default.txt").exists()
    assert (prompts_dir / "planner.txt").exists()
    assert (prompts_dir / "codereviewer.txt").exists()

    # Generated agents must be prefixed with agent- to match Pal role conventions.
    assert (prompts_dir / "agent-alpha.txt").exists()
    assert (prompts_dir / "agent-api-builder.txt").exists()

    # CLI client role mappings should reference the shared builtin prompts.
    cfg_files = list((pal_conf / "cli_clients").glob("*.json"))
    assert cfg_files, "Expected Pal cli_clients configs to be generated"

    # Legacy prompt filenames should be removed to prevent ambiguity/duplication.
    assert not (prompts_dir / "alpha.txt").exists()
    assert not (prompts_dir / "api-builder.txt").exists()
    assert not (prompts_dir / "api.txt").exists()
    assert not (prompts_dir / "codex_default.txt").exists()
    assert not (prompts_dir / "claude_default.txt").exists()
    assert not (prompts_dir / "gemini_default.txt").exists()
