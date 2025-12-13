"""Integration tests for CommandComposer (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.commands import CommandComposer
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager


class _AdapterStub:
    def __init__(self, packs: list[str]) -> None:
        self._packs = packs

    def get_active_packs(self) -> list[str]:
        return self._packs


def _build_context(tmp_path: Path) -> AdapterContext:
    """Create a minimal AdapterContext backed by temp dirs."""
    project_root = tmp_path
    project_dir = project_root / ".edison"
    core_dir = project_root / "core"
    bundled_packs_dir = project_root / "bundled_packs"
    project_packs_dir = project_dir / "packs"

    project_dir.mkdir(parents=True, exist_ok=True)
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "config").mkdir(exist_ok=True)
    (bundled_packs_dir).mkdir(exist_ok=True)
    project_packs_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "config").mkdir(exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub([])

    return AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config={},
        writer=writer,
        adapter=adapter_stub,
    )


def test_command_composer_writes_platform_files(tmp_path: Path) -> None:
    """Test that CommandComposer loads bundled commands and writes them.

    CommandComposer uses ConfigManager which loads bundled commands from
    edison.data/config/commands.yaml. This test verifies that bundled
    commands are properly written to the output directory.
    """
    ctx = _build_context(tmp_path)

    composer = CommandComposer(ctx)
    definitions = composer.compose()

    # Should have bundled commands loaded
    assert len(definitions) > 0, "Should have bundled command definitions"

    # Compose for claude platform
    results = composer.compose_for_platform("claude", definitions)

    # Should write bundled commands (e.g., session-next, task-claim)
    assert len(results) > 0, "Should write command files"

    # Verify at least one known bundled command exists
    known_commands = {"session-next", "session-status", "task-claim", "task-status"}
    found_commands = set(results.keys())
    assert found_commands & known_commands, f"Expected bundled commands, got: {found_commands}"

    # Verify files are actually written
    for cmd_id, out_path in results.items():
        assert out_path.exists(), f"Command file should exist: {out_path}"
        content = out_path.read_text(encoding="utf-8")
        assert len(content) > 0, f"Command file should have content: {cmd_id}"
