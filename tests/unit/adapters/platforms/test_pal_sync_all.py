"""End-to-end smoke for PalAdapter.sync_all (no mocks, minimal setup)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.platforms.pal import PalAdapter


def _setup_generated_agents(tmp_path: Path) -> None:
    gen_agents = tmp_path / ".edison" / "_generated" / "agents"
    gen_agents.mkdir(parents=True, exist_ok=True)
    (gen_agents / "alpha.md").write_text("# Alpha\nAlpha agent.\n", encoding="utf-8")


def test_pal_sync_all_runs(tmp_path: Path) -> None:
    project_root = tmp_path

    _setup_generated_agents(project_root)

    adapter = PalAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Smoke: just assert structure and that Pal output directories exist.
    assert isinstance(result, dict)
    pal_conf = project_root / ".pal" / "conf"
    assert pal_conf.exists()
    # Pal needs CLI client configs (conf/cli_clients) to expose roles to clink.
    assert (pal_conf / "cli_clients").exists()
