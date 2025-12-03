"""End-to-end smoke for CursorAdapter.sync_all (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.platforms.cursor import CursorAdapter
from edison.core.composition.output.writer import CompositionFileWriter


def _setup_generated_agents(tmp_path: Path) -> None:
    gen_agents = tmp_path / ".edison" / "_generated" / "agents"
    gen_agents.mkdir(parents=True, exist_ok=True)
    (gen_agents / "alpha.md").write_text("# Alpha\nAlpha agent.\n", encoding="utf-8")


def _setup_generated_clients(tmp_path: Path) -> None:
    gen_clients = tmp_path / ".edison" / "_generated" / "clients"
    gen_clients.mkdir(parents=True, exist_ok=True)
    (gen_clients / "cursor.md").write_text("# Cursor Client\n", encoding="utf-8")


def test_cursor_sync_all_writes_outputs(tmp_path: Path) -> None:
    project_root = tmp_path
    writer = CompositionFileWriter(base_dir=project_root)
    comp_path = project_root / ".edison" / "config" / "composition.yaml"
    comp_path.parent.mkdir(parents=True, exist_ok=True)
    writer.write_text(comp_path, "")

    _setup_generated_agents(project_root)
    _setup_generated_clients(project_root)

    adapter = CursorAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Agents synced
    agents = result.get("agents", [])
    assert agents, "agents should be synced"
    for p in agents:
        assert Path(p).exists()

    # Cursor rules may be absent in minimal setup; ensure .cursor dir exists
    assert (project_root / ".cursor").exists()
