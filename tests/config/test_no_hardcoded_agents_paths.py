from __future__ import annotations

from pathlib import Path
import re

import pytest


# CRITICAL: Guard against regressions that reintroduce literal ".agents" paths
# into core configuration and library modules. All path resolution must flow
# through PathResolver/SessionContext or config templates instead of hardcoded
# strings.
CRITICAL_PATHS = [
    Path("core/config/defaults.yaml"),
    Path("core/config/delegation.yaml"),
    Path("core/config/session.yaml"),
    Path("core/config/validators.yaml"),
    Path("core/lib/agents.py"),
    Path("core/lib/claude_adapter.py"),
    Path("core/lib/cursor_adapter.py"),
    Path("core/lib/composition/__init__.py"),
    Path("core/lib/paths/project.py"),
    Path("core/lib/rules.py"),
]


@pytest.mark.parametrize("relpath", CRITICAL_PATHS)
def test_no_hardcoded_agents_literals(relpath: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    target = root / relpath
    assert target.exists(), f"Missing critical file: {relpath}"
    text = target.read_text(encoding="utf-8")
    pattern = re.compile(r"[\"']\\.agents")
    assert not pattern.search(text), f"Hardcoded '.agents' literal found in {relpath}"
