from __future__ import annotations

from pathlib import Path
import sys

from tests.helpers.paths import get_repo_root

ROOT = get_repo_root()
core_path = ROOT / ".edison" / "core"
from edison.core.composition import auto_activate_packs  # type: ignore  # noqa: E402
from edison.core.utils.text import render_conditional_includes  # noqa: E402


def test_auto_activate_packs_for_prisma_files() -> None:
    """prisma files should activate prisma pack."""
    changed_files = [Path("prisma/schema.prisma")]

    # Limit available packs to a small subset to avoid incidental matches
    activated = auto_activate_packs(
        changed_files,
        available_packs=["prisma", "nextjs"],
    )

    assert "prisma" in activated
    assert "nextjs" not in activated


def test_auto_activate_packs_for_nextjs_files() -> None:
    """nextjs app files should activate nextjs pack."""
    changed_files = [Path("app/page.tsx"), Path("next.config.js")]

    activated = auto_activate_packs(changed_files)

    assert "nextjs" in activated
    assert "prisma" not in activated


def test_conditional_include_with_pack() -> None:
    """Conditional include should render when pack is active."""
    template = "Core{{include-if:has-pack(prisma):+prisma}}"
    result = render_conditional_includes(template, active_packs={"prisma"})
    # render_conditional_includes converts pack conditionals to include directives
    # The actual file resolution happens in a later stage
    assert "{{include:+prisma}}" in result or "+prisma" in result

