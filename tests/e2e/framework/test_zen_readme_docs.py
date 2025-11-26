"""
Test that Zen MCP documentation is properly included in README.md.

CRITICAL PRINCIPLES:
- NO MOCKS: Tests verify real README file content
- NO HARDCODED VALUES: All commands and paths checked against actual implementation
- STRICT TDD: Tests written FIRST, documentation added SECOND
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path.cwd()
README_PATH = REPO_ROOT / "README.md"
ZEN_SETUP_DOC = REPO_ROOT / "docs" / "ZEN_SETUP.md"


def _read_readme() -> str:
    """Read README.md content."""
    assert README_PATH.exists(), f"README.md not found at {README_PATH}"
    return README_PATH.read_text(encoding="utf-8")


def _read_zen_setup_doc() -> str:
    """Read docs/ZEN_SETUP.md content."""
    assert ZEN_SETUP_DOC.exists(), f"ZEN_SETUP.md not found at {ZEN_SETUP_DOC}"
    return ZEN_SETUP_DOC.read_text(encoding="utf-8")


def test_readme_has_zen_section():
    """README must contain a Zen MCP Integration section."""
    content = _read_readme()
    assert "## Zen MCP Integration" in content, (
        "README.md must contain '## Zen MCP Integration' section"
    )


def test_readme_mentions_zen_mcp_server():
    """README must mention zen-mcp-server."""
    content = _read_readme()
    assert "zen-mcp-server" in content, (
        "README.md must mention zen-mcp-server"
    )


def test_readme_has_edison_init_command():
    """README must document 'edison init' command for Zen setup."""
    content = _read_readme()
    assert "edison init" in content, (
        "README.md must document 'edison init' command"
    )


def test_readme_has_edison_zen_setup_command():
    """README must document 'edison zen setup' command."""
    content = _read_readme()
    assert "edison zen setup" in content, (
        "README.md must document 'edison zen setup' command"
    )


def test_readme_has_edison_zen_configure_command():
    """README must document 'edison zen configure' command."""
    content = _read_readme()
    assert "edison zen configure" in content, (
        "README.md must document 'edison zen configure' command"
    )


def test_readme_has_edison_zen_start_server_command():
    """README must document 'edison zen start-server' command."""
    content = _read_readme()
    # The actual command is 'edison zen start-server' (with hyphen)
    assert re.search(r"edison zen start-server", content), (
        "README.md must document 'edison zen start-server' command"
    )


def test_readme_has_uvx_installation():
    """README must mention uvx/uv installation."""
    content = _read_readme()
    assert "uvx" in content or "pip install uv" in content, (
        "README.md must mention uvx or 'pip install uv'"
    )


def test_readme_has_check_flag():
    """README must document --check flag for zen setup."""
    content = _read_readme()
    assert "--check" in content, (
        "README.md must document --check flag for verifying setup"
    )


def test_readme_links_to_zen_setup_doc():
    """README must link to docs/ZEN_SETUP.md for detailed setup."""
    content = _read_readme()
    assert "docs/ZEN_SETUP.md" in content, (
        "README.md must link to docs/ZEN_SETUP.md for detailed documentation"
    )


def test_readme_mentions_mcp_json():
    """README must mention .mcp.json configuration."""
    content = _read_readme()
    assert ".mcp.json" in content, (
        "README.md must mention .mcp.json configuration"
    )


def test_zen_setup_doc_exists():
    """docs/ZEN_SETUP.md must exist."""
    assert ZEN_SETUP_DOC.exists(), (
        f"docs/ZEN_SETUP.md must exist at {ZEN_SETUP_DOC}"
    )


def test_zen_setup_doc_has_overview():
    """ZEN_SETUP.md must have an overview section."""
    content = _read_zen_setup_doc()
    assert "## Overview" in content or "# Overview" in content, (
        "ZEN_SETUP.md must contain an Overview section"
    )


def test_zen_setup_doc_has_prerequisites():
    """ZEN_SETUP.md must list prerequisites."""
    content = _read_zen_setup_doc()
    assert "## Prerequisites" in content or "Prerequisites" in content, (
        "ZEN_SETUP.md must contain Prerequisites section"
    )


def test_zen_setup_doc_mentions_python_version():
    """ZEN_SETUP.md must mention Python version requirement."""
    content = _read_zen_setup_doc()
    assert re.search(r"Python 3\.\d+", content), (
        "ZEN_SETUP.md must mention Python version requirement (e.g., Python 3.10+)"
    )


def test_zen_setup_doc_has_installation_methods():
    """ZEN_SETUP.md must document installation methods."""
    content = _read_zen_setup_doc()
    assert "## Installation" in content or "Installation Methods" in content, (
        "ZEN_SETUP.md must contain Installation section"
    )


def test_zen_setup_doc_has_automatic_setup():
    """ZEN_SETUP.md must document automatic setup via edison init."""
    content = _read_zen_setup_doc()
    assert "edison init" in content, (
        "ZEN_SETUP.md must document automatic setup via 'edison init'"
    )


def test_zen_setup_doc_has_manual_setup():
    """ZEN_SETUP.md must document manual setup steps."""
    content = _read_zen_setup_doc()
    assert "Manual" in content or "manual" in content, (
        "ZEN_SETUP.md must document manual setup option"
    )


def test_zen_setup_doc_has_troubleshooting():
    """ZEN_SETUP.md must have a troubleshooting section."""
    content = _read_zen_setup_doc()
    assert "## Troubleshooting" in content or "Troubleshooting" in content, (
        "ZEN_SETUP.md must contain Troubleshooting section"
    )


def test_zen_setup_doc_has_github_link():
    """ZEN_SETUP.md must link to zen-mcp-server GitHub repo."""
    content = _read_zen_setup_doc()
    assert "github.com/BeehiveInnovations/zen-mcp-server" in content, (
        "ZEN_SETUP.md must link to zen-mcp-server GitHub repository"
    )


def test_no_hardcoded_absolute_paths():
    """Documentation must not contain hardcoded absolute paths."""
    readme_content = _read_readme()
    zen_doc_content = _read_zen_setup_doc()

    # Check for common hardcoded path patterns
    hardcoded_patterns = [
        r"/Users/[^/\s]+",  # macOS user paths
        r"C:\\Users\\",     # Windows user paths
        r"/home/[^/\s]+",   # Linux user paths
    ]

    for pattern in hardcoded_patterns:
        assert not re.search(pattern, readme_content), (
            f"README.md contains hardcoded absolute path matching {pattern}"
        )
        assert not re.search(pattern, zen_doc_content), (
            f"ZEN_SETUP.md contains hardcoded absolute path matching {pattern}"
        )


def test_commands_use_relative_paths():
    """Commands in docs must use relative paths or placeholders."""
    readme_content = _read_readme()
    zen_doc_content = _read_zen_setup_doc()

    # Find all edison zen configure commands
    configure_cmds = re.findall(
        r"edison zen configure\s+([^\s\n]+)",
        readme_content + zen_doc_content
    )

    for cmd_arg in configure_cmds:
        # Should be either:
        # - A relative path (., .., ./path)
        # - A placeholder (/path/to/project)
        # - No argument (defaults to current dir)
        assert not cmd_arg.startswith("/Users/") and not cmd_arg.startswith("/home/"), (
            f"Command argument should not be an absolute user path: {cmd_arg}"
        )


def test_readme_zen_section_after_usage():
    """Zen MCP Integration section should appear after Usage section."""
    content = _read_readme()

    usage_pos = content.find("## Usage")
    zen_pos = content.find("## Zen MCP Integration")

    assert usage_pos != -1, "README.md must have ## Usage section"
    assert zen_pos != -1, "README.md must have ## Zen MCP Integration section"
    assert zen_pos > usage_pos, (
        "## Zen MCP Integration should appear after ## Usage section"
    )


def test_zen_setup_doc_no_duplicate_headers():
    """ZEN_SETUP.md should not have duplicate section headers."""
    content = _read_zen_setup_doc()

    # Extract all headers
    headers = re.findall(r"^#{1,3}\s+(.+)$", content, re.MULTILINE)

    # Check for duplicates
    seen = set()
    duplicates = set()
    for header in headers:
        normalized = header.strip().lower()
        if normalized in seen:
            duplicates.add(header)
        seen.add(normalized)

    assert not duplicates, (
        f"ZEN_SETUP.md contains duplicate headers: {duplicates}"
    )
