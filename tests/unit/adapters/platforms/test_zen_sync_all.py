"""End-to-end smoke for ZenAdapter.sync_all (no mocks, minimal setup)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.platforms.zen.adapter import ZenAdapter
from edison.core.composition.output.writer import CompositionFileWriter


def _setup_generated_agents(tmp_path: Path) -> None:
    gen_agents = tmp_path / ".edison" / "_generated" / "agents"
    gen_agents.mkdir(parents=True, exist_ok=True)
    (gen_agents / "alpha.md").write_text("# Alpha\nAlpha agent.\n", encoding="utf-8")


def test_zen_sync_all_runs(tmp_path: Path) -> None:
    project_root = tmp_path
    writer = CompositionFileWriter(base_dir=project_root)
    comp_path = project_root / ".edison" / "config" / "composition.yaml"
    comp_path.parent.mkdir(parents=True, exist_ok=True)
    writer.write_text(comp_path, "")

    _setup_generated_agents(project_root)

    adapter = ZenAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Should return roles mapping or similar; just assert no error and paths exist
    assert isinstance(result, dict)
    roles = result.get("roles", {})
    if roles:
        for paths in roles.values():
            for p in paths:
                assert Path(p).exists()
