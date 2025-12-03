"""Integration tests for HookComposer (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.hooks import HookComposer
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager


class _AdapterStub:
    def __init__(self, packs: list[str]) -> None:
        self._packs = packs

    def get_active_packs(self) -> list[str]:
        return self._packs


def _build_context(tmp_path: Path, config: dict) -> AdapterContext:
    project_root = tmp_path
    project_dir = project_root / ".edison"
    core_dir = project_root / "core"
    bundled_packs_dir = project_root / "bundled_packs"
    project_packs_dir = project_dir / "packs"

    project_dir.mkdir(parents=True, exist_ok=True)
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "config").mkdir(exist_ok=True)
    (core_dir / "templates" / "hooks").mkdir(parents=True, exist_ok=True)
    (project_dir / "templates" / "hooks").mkdir(parents=True, exist_ok=True)
    bundled_packs_dir.mkdir(exist_ok=True)
    project_packs_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "config").mkdir(exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub([])

    ctx = AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config=config,
        writer=writer,
        adapter=adapter_stub,
    )
    # Minimal bundled hooks config to avoid auto-generated defaults
    bundled_hooks = core_dir / "config" / "hooks.yaml"
    if not bundled_hooks.exists():
        bundled_hooks.write_text("hooks:\n  definitions: {}\n", encoding="utf-8")

    return ctx


def test_hook_composer_renders_core_hook(tmp_path: Path) -> None:
    ctx = _build_context(
        tmp_path,
        config={"hooks": {"enabled": True, "platforms": ["claude"]}},
    )

    # Project hook definition (overlays bundled defaults)
    hooks_yaml = ctx.project_dir / "config" / "hooks.yml"
    hooks_yaml.write_text(
        """
hooks:
  definitions:
    sample:
      type: PreToolUse
      description: run sample hook
      template: sample.hook
""",
        encoding="utf-8",
    )

    # Hook template placed in project templates
    template = ctx.project_dir / "templates" / "hooks" / "sample.hook"
    template.write_text("#!/bin/bash\necho sample\n", encoding="utf-8")

    composer = HookComposer(ctx)
    results = composer.compose_hooks()

    # At least one hook is generated and includes our template content
    assert results
    found = any(path.read_text(encoding="utf-8").find("sample") != -1 for path in results.values())
    assert found
