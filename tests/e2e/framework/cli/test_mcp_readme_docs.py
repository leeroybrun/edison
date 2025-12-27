"""
README and docs must describe the generic MCP setup flow.

CRITICAL PRINCIPLES:
- NO MOCKS: Tests verify real README file content
- NO HARDCODED VALUES: Assertions align with YAML-driven commands
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path.cwd()
README_PATH = REPO_ROOT / "README.md"
PAL_SETUP_DOC = REPO_ROOT / "docs" / "PAL_SETUP.md"


def _read_readme() -> str:
    assert README_PATH.exists(), f"README.md not found at {README_PATH}"
    return README_PATH.read_text(encoding="utf-8")


def test_readme_has_mcp_section():
    content = _read_readme()
    assert "MCP" in content and "mcp setup" in content.lower(), (
        "README.md must describe MCP integration and commands"
    )


def test_readme_mentions_mcp_commands():
    content = _read_readme()
    assert re.search(r"edison mcp setup", content, re.IGNORECASE), "README must mention edison mcp setup"
    assert re.search(r"edison mcp configure", content, re.IGNORECASE), "README must mention edison mcp configure"


def test_readme_mentions_mcp_config_files():
    content = _read_readme()
    assert ".mcp.json" in content, "README must mention .mcp.json"
    assert "mcp.yaml" in content.lower(), "README must mention mcp.yaml configuration source"


def test_readme_links_to_setup_doc():
    content = _read_readme()
    assert "docs/PAL_SETUP.md" in content, "README must link to PAL_SETUP.md (setup instructions)"
    assert PAL_SETUP_DOC.exists(), "docs/PAL_SETUP.md must exist"
