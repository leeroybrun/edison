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
    ctx = _build_context(tmp_path)

    # Core commands config
    commands_yaml = ctx.core_dir / "config" / "commands.yaml"
    commands_yaml.write_text(
        """
commands:
  definitions:
    - id: hello
      domain: general
      command: hello-world
      short_desc: Say hello
      full_desc: Prints hello
      cli: hello
      args: []
      when_to_use: anytime
      related_commands: []
""",
        encoding="utf-8",
    )

    composer = CommandComposer(ctx)
    results = composer.compose_for_platform("claude", composer.compose())

    # Should write a markdown file to .claude/commands/
    assert "hello" in results
    out_path = results["hello"]
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "hello-world" in content
    assert "Say hello" in content
