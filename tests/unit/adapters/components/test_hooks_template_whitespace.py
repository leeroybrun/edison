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
    user_dir = project_root / ".edison-user"
    core_dir = project_root / "core"
    bundled_packs_dir = project_root / "bundled_packs"
    user_packs_dir = user_dir / "packs"
    project_packs_dir = project_dir / "packs"

    for d in (
        project_dir,
        user_dir,
        core_dir,
        bundled_packs_dir,
        user_packs_dir,
        project_packs_dir,
        core_dir / "config",
        project_dir / "config",
        project_dir / "templates" / "hooks",
    ):
        d.mkdir(parents=True, exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub([])

    # Minimal bundled hooks config to avoid auto-generated defaults
    bundled_hooks = core_dir / "config" / "hooks.yaml"
    if not bundled_hooks.exists():
        bundled_hooks.write_text("hooks:\n  definitions: {}\n", encoding="utf-8")

    return AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        user_dir=user_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        user_packs_dir=user_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config=config,
        writer=writer,
        adapter=adapter_stub,
    )


def test_hook_template_block_lines_do_not_emit_blank_lines(tmp_path: Path) -> None:
    """Regression: tag-only lines should not become blank lines in rendered scripts."""
    ctx = _build_context(tmp_path, config={"hooks": {"enabled": True, "platforms": ["claude"]}})

    # Project hook definition
    (ctx.project_dir / "config" / "hooks.yml").write_text(
        """
hooks:
  definitions:
    sample:
      type: PreToolUse
      description: sample hook
      template: sample.sh.template
      config:
        flag: true
""".lstrip(),
        encoding="utf-8",
    )

    # Template designed so that any block-tag whitespace becomes visible as blank lines.
    (ctx.project_dir / "templates" / "hooks" / "sample.sh.template").write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "echo one",
                "{% if config.get('flag') %}",
                "echo two",
                "{% endif %}",
                "echo three",
                "",
            ]
        ),
        encoding="utf-8",
    )

    composer = HookComposer(ctx)
    scripts = composer.compose_hooks(output_dir_override=(tmp_path / ".claude" / "hooks"))

    out_path = scripts["sample"]
    content = out_path.read_text(encoding="utf-8")

    # With trimmed Jinja blocks, we should not get blank lines from the tag-only lines.
    assert content.splitlines() == [
        "#!/usr/bin/env bash",
        "echo one",
        "echo two",
        "echo three",
    ]

