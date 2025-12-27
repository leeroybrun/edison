"""
Tests for dependency detection utilities.

STRICT TDD: These tests are written FIRST to drive implementation.
NO MOCKS: Uses dependency injection for all system interactions.
"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Union

import pytest

from edison.core.utils.dependencies import UvxStatus, detect_uvx, detect_pal_mcp_server


# --- Test Helpers ---

class FakeRun:
    """Fake implementation of subprocess.run."""
    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "",
        side_effect: Optional[Exception] = None
    ):
        self.returncode = returncode
        self.stdout = stdout
        self.side_effect = side_effect

    def __call__(self, *args, **kwargs):
        if self.side_effect:
            raise self.side_effect
        
        # Simple result object mimicking subprocess.CompletedProcess
        class Result:
            def __init__(self, rc, out):
                self.returncode = rc
                self.stdout = out
        return Result(self.returncode, self.stdout)


def make_fake_which(mapping: Dict[str, str]) -> Any:
    """Create a fake which_func that looks up commands in a mapping."""
    def fake_which(cmd: str) -> Optional[str]:
        return mapping.get(cmd)
    return fake_which


def make_fake_env_get(env_vars: Dict[str, str]) -> Any:
    """Create a fake env_get that looks up variables in a dict."""
    def fake_env_get(key: str, default: Optional[str] = None) -> Optional[str]:
        return env_vars.get(key, default)
    return fake_env_get


def make_fake_home(path: Path) -> Any:
    """Create a fake home_func that returns a specific path."""
    def fake_home() -> Path:
        return path
    return fake_home


class FakeUvxDetector:
    """Fake implementation of detect_uvx."""
    def __init__(self, status: UvxStatus):
        self.status = status

    def __call__(self) -> UvxStatus:
        return self.status


# --- Tests ---

class TestDetectUvx:
    """Test uvx detection utility."""

    def test_detect_uvx_when_available_returns_status_with_version(self):
        """Test: detect_uvx returns available=True with version when uvx is in PATH."""
        fake_which = make_fake_which({"uvx": "/usr/local/bin/uvx"})
        fake_run = FakeRun(returncode=0, stdout="uv 0.1.0\n")

        result = detect_uvx(which_func=fake_which, run_func=fake_run)

        assert result.available is True
        assert result.version == "uv 0.1.0"
        assert result.path == "/usr/local/bin/uvx"
        assert result.install_instruction == ""

    def test_detect_uvx_when_not_available_returns_install_instructions(self):
        """Test: detect_uvx returns available=False with install instructions when uvx not found."""
        fake_which = make_fake_which({})
        # run_func shouldn't be called if which returns None, but providing a dummy just in case
        fake_run = FakeRun()

        result = detect_uvx(which_func=fake_which, run_func=fake_run)

        assert result.available is False
        assert result.version is None
        assert result.path is None
        assert "uvx not found" in result.install_instruction
        assert "pip install uv" in result.install_instruction

    def test_detect_uvx_when_uv_exists_but_not_uvx_provides_specific_guidance(self):
        """Test: detect_uvx provides specific guidance when uv is installed but uvx is not."""
        fake_which = make_fake_which({"uv": "/usr/local/bin/uv"})
        
        result = detect_uvx(which_func=fake_which)

        assert result.available is False
        assert result.version is None
        assert result.path is None
        assert "uv is installed but uvx not found" in result.install_instruction
        assert "uv tool install uvx" in result.install_instruction

    def test_detect_uvx_handles_subprocess_timeout(self):
        """Test: detect_uvx handles subprocess timeout gracefully."""
        fake_which = make_fake_which({"uvx": "/usr/local/bin/uvx"})
        fake_run = FakeRun(side_effect=subprocess.TimeoutExpired("uvx", 10))

        result = detect_uvx(which_func=fake_which, run_func=fake_run)

        # Should fall back to "not found" behavior (checks for uv next)
        assert result.available is False

    def test_detect_uvx_handles_subprocess_error(self):
        """Test: detect_uvx handles subprocess errors gracefully."""
        fake_which = make_fake_which({"uvx": "/usr/local/bin/uvx"})
        fake_run = FakeRun(side_effect=subprocess.SubprocessError("error"))

        result = detect_uvx(which_func=fake_which, run_func=fake_run)

        # Should fall back to "not found" behavior
        assert result.available is False

    def test_detect_uvx_when_version_check_fails_returns_not_available(self):
        """Test: detect_uvx returns not available when version check returns non-zero."""
        fake_which = make_fake_which({"uvx": "/usr/local/bin/uvx"})
        fake_run = FakeRun(returncode=1, stdout="")

        result = detect_uvx(which_func=fake_which, run_func=fake_run)

        assert result.available is False


class TestDetectPalMcpServer:
    """Test pal-mcp-server detection utility."""

    def test_detect_pal_mcp_server_finds_env_var_installation(self, tmp_path):
        """Test: detect_pal_mcp_server detects installation from PAL_MCP_SERVER_DIR env var."""
        pal_dir = tmp_path / "custom-pal"
        pal_dir.mkdir()
        (pal_dir / "pyproject.toml").write_text("[project]\nname='pal'")

        fake_env = make_fake_env_get({"PAL_MCP_SERVER_DIR": str(pal_dir)})
        
        # Other deps not needed for this path but required by signature
        fake_home = make_fake_home(tmp_path)
        fake_uvx = FakeUvxDetector(UvxStatus(False, None, None, ""))

        available, path = detect_pal_mcp_server(
            env_get=fake_env,
            home_func=fake_home,
            uvx_detector=fake_uvx
        )

        assert available is True
        assert path == pal_dir

    def test_detect_pal_mcp_server_finds_home_installation(self, tmp_path):
        """Test: detect_pal_mcp_server detects installation in home directory."""
        pal_dir = tmp_path / "pal-mcp-server"
        pal_dir.mkdir()
        (pal_dir / "pyproject.toml").write_text("[project]\nname='pal'")

        fake_env = make_fake_env_get({})
        fake_home = make_fake_home(tmp_path)
        fake_uvx = FakeUvxDetector(UvxStatus(False, None, None, ""))

        available, path = detect_pal_mcp_server(
            env_get=fake_env,
            home_func=fake_home,
            uvx_detector=fake_uvx
        )

        assert available is True
        assert path == pal_dir

    def test_detect_pal_mcp_server_returns_true_when_uvx_available(self, tmp_path):
        """Test: detect_pal_mcp_server returns available=True when uvx is available."""
        fake_env = make_fake_env_get({})
        fake_home = make_fake_home(tmp_path / "nonexistent")
        
        uvx_status = UvxStatus(
            available=True,
            version="0.1.0",
            path="/usr/bin/uvx",
            install_instruction=""
        )
        fake_uvx = FakeUvxDetector(uvx_status)

        available, path = detect_pal_mcp_server(
            env_get=fake_env,
            home_func=fake_home,
            uvx_detector=fake_uvx
        )

        assert available is True
        assert path is None  # No local path, will use uvx

    def test_detect_pal_mcp_server_returns_false_when_nothing_found(self, tmp_path):
        """Test: detect_pal_mcp_server returns available=False when nothing is found."""
        fake_env = make_fake_env_get({})
        fake_home = make_fake_home(tmp_path / "nonexistent")
        
        uvx_status = UvxStatus(
            available=False,
            version=None,
            path=None,
            install_instruction="Install uvx"
        )
        fake_uvx = FakeUvxDetector(uvx_status)

        available, path = detect_pal_mcp_server(
            env_get=fake_env,
            home_func=fake_home,
            uvx_detector=fake_uvx
        )

        assert available is False
        assert path is None

    def test_detect_pal_mcp_server_env_var_takes_precedence(self, tmp_path):
        """Test: detect_pal_mcp_server prioritizes PAL_MCP_SERVER_DIR over home directory."""
        # Create both installations
        env_pal = tmp_path / "env-pal"
        env_pal.mkdir()
        (env_pal / "pyproject.toml").write_text("[project]\nname='pal-env'")

        home_pal = tmp_path / "pal-mcp-server"
        home_pal.mkdir()
        (home_pal / "pyproject.toml").write_text("[project]\nname='pal-home'")

        fake_env = make_fake_env_get({"PAL_MCP_SERVER_DIR": str(env_pal)})
        fake_home = make_fake_home(tmp_path)
        fake_uvx = FakeUvxDetector(UvxStatus(False, None, None, ""))

        available, path = detect_pal_mcp_server(
            env_get=fake_env,
            home_func=fake_home,
            uvx_detector=fake_uvx
        )

        assert available is True
        assert path == env_pal  # Should return env var path, not home

    def test_detect_pal_mcp_server_requires_pyproject_toml(self, tmp_path):
        """Test: detect_pal_mcp_server requires pyproject.toml to be present."""
        pal_dir = tmp_path / "pal-mcp-server"
        pal_dir.mkdir()
        # No pyproject.toml

        fake_env = make_fake_env_get({})
        fake_home = make_fake_home(tmp_path)
        
        uvx_status = UvxStatus(
            available=False,
            version=None,
            path=None,
            install_instruction="Install uvx"
        )
        fake_uvx = FakeUvxDetector(uvx_status)

        available, path = detect_pal_mcp_server(
            env_get=fake_env,
            home_func=fake_home,
            uvx_detector=fake_uvx
        )

        assert available is False
        assert path is None