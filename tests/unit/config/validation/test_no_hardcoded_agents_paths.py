from __future__ import annotations

from pathlib import Path
import re

import pytest

from edison.data import get_data_path
from tests.helpers.paths import get_repo_root


# CRITICAL: Guard against regressions that reintroduce literal ".agents" paths
# into core configuration and library modules. All path resolution must flow
# through PathResolver/SessionContext or config templates instead of hardcoded
# strings.
#
# Updated for bundled data structure - configs now in src/edison/data/config/
CRITICAL_PATHS = [
    ("config", "defaults.yaml"),
    ("config", "delegation.yaml"),
    ("config", "session.yaml"),
    ("config", "validators.yaml"),
]

# Core library paths (not in bundled data)
CORE_LIB_PATHS = [
    Path("src/edison/core/config/__init__.py"),
    Path("src/edison/core/config/manager.py"),
    Path("src/edison/core/paths/resolver.py"),
]


@pytest.mark.parametrize("subpackage,filename", CRITICAL_PATHS)
def test_no_hardcoded_agents_literals_in_data(subpackage: str, filename: str) -> None:
    """Check bundled data files for hardcoded .agents paths."""
    target = get_data_path(subpackage, filename)
    assert target.exists(), f"Missing critical file: {subpackage}/{filename}"
    text = target.read_text(encoding="utf-8")
    pattern = re.compile(r"[\"']\\.agents")
    assert not pattern.search(text), f"Hardcoded '.agents' literal found in {subpackage}/{filename}"


@pytest.mark.parametrize("relpath", CORE_LIB_PATHS)
def test_no_hardcoded_agents_literals_in_lib(relpath: Path) -> None:
    """Check core library modules for hardcoded .agents paths."""
    root = get_repo_root()
    target = root / relpath
    if not target.exists():
        pytest.skip(f"File not found: {relpath}")
    text = target.read_text(encoding="utf-8")
    pattern = re.compile(r"[\"']\\.agents")
    assert not pattern.search(text), f"Hardcoded '.agents' literal found in {relpath}"
