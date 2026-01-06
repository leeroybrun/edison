"""Tests for OpenCode template name validation."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "name",
    [
        "../evil",
        "..",
        "a/b",
        r"a\\b",
        "a..",
        "a.md",
        "",
        " ",
    ],
)
def test_agent_template_rejects_invalid_template_name(name: str, tmp_path: Path) -> None:
    """Agent template rendering should reject names that could traverse paths."""
    from edison.core.adapters.platforms.opencode import (
        OpenCodeAdapterError,
        _render_agent_template,
    )

    with pytest.raises(OpenCodeAdapterError):
        _render_agent_template(name, repo_root=tmp_path)


@pytest.mark.parametrize(
    "name",
    [
        "../evil",
        "..",
        "a/b",
        r"a\\b",
        "a..",
        "a.md",
        "",
        " ",
    ],
)
def test_command_template_rejects_invalid_template_name(name: str, tmp_path: Path) -> None:
    """Command template rendering should reject names that could traverse paths."""
    from edison.core.adapters.platforms.opencode import (
        OpenCodeAdapterError,
        _render_command_template,
    )

    with pytest.raises(OpenCodeAdapterError):
        _render_command_template(name, repo_root=tmp_path)

