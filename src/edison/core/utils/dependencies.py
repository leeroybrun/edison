"""Dependency detection utilities for Edison."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class UvxStatus:
    """Status information for uvx availability."""

    available: bool
    version: Optional[str]
    path: Optional[str]
    install_instruction: str


def detect_uvx() -> UvxStatus:
    """
    Detect uvx availability and provide installation guidance.

    Returns:
        UvxStatus with availability info and install instructions
    """
    # Check if uvx is in PATH
    uvx_path = shutil.which("uvx")

    if uvx_path:
        try:
            result = subprocess.run(
                ["uvx", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return UvxStatus(
                    available=True,
                    version=version,
                    path=uvx_path,
                    install_instruction="",
                )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

    # Check if uv is available (uvx comes with uv)
    uv_path = shutil.which("uv")
    if uv_path:
        return UvxStatus(
            available=False,
            version=None,
            path=None,
            install_instruction="uv is installed but uvx not found. Try: uv tool install uvx",
        )

    # Neither available - provide installation options
    return UvxStatus(
        available=False,
        version=None,
        path=None,
        install_instruction="""uvx not found. Install options:
  1. pip install uv (recommended)
  2. curl -LsSf https://astral.sh/uv/install.sh | sh
  3. brew install uv (macOS)""",
    )


def detect_zen_mcp_server() -> tuple[bool, Optional[Path]]:
    """
    Detect if zen-mcp-server is available.

    Returns:
        Tuple of (available: bool, path: Optional[Path])
    """
    # Check environment variable first
    env_path = os.environ.get("ZEN_MCP_SERVER_DIR")
    if env_path:
        path = Path(env_path)
        if path.exists() and (path / "pyproject.toml").exists():
            return True, path

    # Check standard location
    home_path = Path.home() / "zen-mcp-server"
    if home_path.exists() and (home_path / "pyproject.toml").exists():
        return True, home_path

    # Check if available via uvx
    uvx_status = detect_uvx()
    if uvx_status.available:
        # uvx will auto-install on first use
        return True, None

    return False, None
