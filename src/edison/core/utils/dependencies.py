"""Dependency detection utilities for Edison."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass
class UvxStatus:
    """Status information for uvx availability."""

    available: bool
    version: Optional[str]
    path: Optional[str]
    install_instruction: str


def detect_uvx(
    which_func: Callable[[str], Optional[str]] = shutil.which,
    run_func: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> UvxStatus:
    """
    Detect uvx availability and provide installation guidance.

    Args:
        which_func: Function to locate a command (defaults to shutil.which)
        run_func: Function to run a subprocess (defaults to subprocess.run)

    Returns:
        UvxStatus with availability info and install instructions
    """
    # Check if uvx is in PATH
    uvx_path = which_func("uvx")

    if uvx_path:
        try:
            result = run_func(
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
    uv_path = which_func("uv")
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


def detect_pal_mcp_server(
    env_get: Callable[[str, Optional[str]], Optional[str]] = os.environ.get,
    home_func: Callable[[], Path] = Path.home,
    uvx_detector: Callable[[], UvxStatus] = detect_uvx,
) -> tuple[bool, Optional[Path]]:
    """
    Detect if pal-mcp-server is available.

    Args:
        env_get: Function to get environment variables (defaults to os.environ.get)
        home_func: Function to get home directory (defaults to Path.home)
        uvx_detector: Function to detect uvx (defaults to detect_uvx)

    Returns:
        Tuple of (available: bool, path: Optional[Path])
    """
    # Check environment variable first
    env_path = env_get("PAL_MCP_SERVER_DIR", None)
    if env_path:
        path = Path(env_path)
        if path.exists() and (path / "pyproject.toml").exists():
            return True, path

    # Check standard location
    home_path = home_func() / "pal-mcp-server"
    if home_path.exists() and (home_path / "pyproject.toml").exists():
        return True, home_path

    # Check if available via uvx
    uvx_status = uvx_detector()
    if uvx_status.available:
        # uvx will auto-install on first use
        return True, None

    return False, None