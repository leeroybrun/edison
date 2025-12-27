from __future__ import annotations

from pathlib import Path

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.commands import CommandArg, CommandComposer, CommandDefinition
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager


class _AdapterStub:
    def __init__(self, packs: list[str]) -> None:
        self._packs = packs

    def get_active_packs(self) -> list[str]:
        return self._packs


def _build_context(tmp_path: Path) -> AdapterContext:
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
        project_dir / "config",
    ):
        d.mkdir(parents=True, exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub([])

    return AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        user_dir=user_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        user_packs_dir=user_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config={},
        writer=writer,
        adapter=adapter_stub,
    )


def _frontmatter_block(text: str) -> list[str]:
    lines = text.splitlines()
    assert lines[0] == "---"

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            end_idx = i
            break
    assert end_idx is not None, "Expected closing '---' for YAML frontmatter"
    return lines[1:end_idx]


def test_claude_command_frontmatter_has_no_blank_lines(tmp_path: Path) -> None:
    """Render Claude command markdown without Jinja block-tag blank line artifacts.

    Regression: Our Jinja templates include `{% if ... %}` / `{% endif %}` blocks on
    their own lines. With default Jinja whitespace rules, those lines become empty
    lines in the rendered output (especially within YAML frontmatter).
    """
    ctx = _build_context(tmp_path)
    composer = CommandComposer(ctx)

    cmd = CommandDefinition(
        id="demo",
        domain="qa",
        command="demo",
        short_desc="Demo command",
        full_desc="Demo full description.",
        cli="edison demo",
        args=[CommandArg(name="arg1", description="Arg 1", required=True)],
        when_to_use="- Use when demoing",
        related_commands=["rules-current"],
    )

    out_dir = tmp_path / ".claude" / "commands"
    result = composer.compose_for_platform("claude", [cmd], output_dir_override=out_dir)
    out_path = result["demo"]
    content = out_path.read_text(encoding="utf-8")

    frontmatter = _frontmatter_block(content)
    assert frontmatter, "Expected non-empty YAML frontmatter"
    assert all(line.strip() != "" for line in frontmatter), frontmatter

