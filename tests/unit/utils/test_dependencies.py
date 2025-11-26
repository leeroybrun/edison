"""
Tests for dependency detection utilities.

STRICT TDD: These tests are written FIRST to drive implementation.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from edison.core.utils.dependencies import UvxStatus, detect_uvx, detect_zen_mcp_server


class TestDetectUvx:
    """Test uvx detection utility."""

    def test_detect_uvx_when_available_returns_status_with_version(self):
        """Test: detect_uvx returns available=True with version when uvx is in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/uvx"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="uv 0.1.0\n"
                )

                result = detect_uvx()

                assert result.available is True
                assert result.version == "uv 0.1.0"
                assert result.path == "/usr/local/bin/uvx"
                assert result.install_instruction == ""

    def test_detect_uvx_when_not_available_returns_install_instructions(self):
        """Test: detect_uvx returns available=False with install instructions when uvx not found."""
        with patch("shutil.which", return_value=None):
            result = detect_uvx()

            assert result.available is False
            assert result.version is None
            assert result.path is None
            assert "uvx not found" in result.install_instruction
            assert "pip install uv" in result.install_instruction

    def test_detect_uvx_when_uv_exists_but_not_uvx_provides_specific_guidance(self):
        """Test: detect_uvx provides specific guidance when uv is installed but uvx is not."""
        def which_side_effect(cmd):
            if cmd == "uvx":
                return None
            if cmd == "uv":
                return "/usr/local/bin/uv"
            return None

        with patch("shutil.which", side_effect=which_side_effect):
            result = detect_uvx()

            assert result.available is False
            assert result.version is None
            assert result.path is None
            assert "uv is installed but uvx not found" in result.install_instruction
            assert "uv tool install uvx" in result.install_instruction

    def test_detect_uvx_handles_subprocess_timeout(self):
        """Test: detect_uvx handles subprocess timeout gracefully."""
        with patch("shutil.which", return_value="/usr/local/bin/uvx"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("uvx", 10)):
                result = detect_uvx()

                # Should fall back to "not found" behavior
                assert result.available is False

    def test_detect_uvx_handles_subprocess_error(self):
        """Test: detect_uvx handles subprocess errors gracefully."""
        with patch("shutil.which", return_value="/usr/local/bin/uvx"):
            with patch("subprocess.run", side_effect=subprocess.SubprocessError("error")):
                result = detect_uvx()

                # Should fall back to "not found" behavior
                assert result.available is False

    def test_detect_uvx_when_version_check_fails_returns_not_available(self):
        """Test: detect_uvx returns not available when version check returns non-zero."""
        with patch("shutil.which", return_value="/usr/local/bin/uvx"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="")

                result = detect_uvx()

                assert result.available is False


class TestDetectZenMcpServer:
    """Test zen-mcp-server detection utility."""

    def test_detect_zen_mcp_server_finds_env_var_installation(self, tmp_path):
        """Test: detect_zen_mcp_server detects installation from ZEN_MCP_SERVER_DIR env var."""
        zen_dir = tmp_path / "custom-zen"
        zen_dir.mkdir()
        (zen_dir / "pyproject.toml").write_text("[project]\nname='zen'")

        with patch.dict("os.environ", {"ZEN_MCP_SERVER_DIR": str(zen_dir)}):
            available, path = detect_zen_mcp_server()

            assert available is True
            assert path == zen_dir

    def test_detect_zen_mcp_server_finds_home_installation(self, tmp_path):
        """Test: detect_zen_mcp_server detects installation in home directory."""
        zen_dir = tmp_path / "zen-mcp-server"
        zen_dir.mkdir()
        (zen_dir / "pyproject.toml").write_text("[project]\nname='zen'")

        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                available, path = detect_zen_mcp_server()

                assert available is True
                assert path == zen_dir

    def test_detect_zen_mcp_server_returns_true_when_uvx_available(self):
        """Test: detect_zen_mcp_server returns available=True when uvx is available."""
        with patch("pathlib.Path.home", return_value=Path("/nonexistent")):
            with patch.dict("os.environ", {}, clear=True):
                with patch("edison.core.utils.dependencies.detect_uvx") as mock_detect:
                    mock_detect.return_value = UvxStatus(
                        available=True,
                        version="0.1.0",
                        path="/usr/bin/uvx",
                        install_instruction=""
                    )

                    available, path = detect_zen_mcp_server()

                    assert available is True
                    assert path is None  # No local path, will use uvx

    def test_detect_zen_mcp_server_returns_false_when_nothing_found(self):
        """Test: detect_zen_mcp_server returns available=False when nothing is found."""
        with patch("pathlib.Path.home", return_value=Path("/nonexistent")):
            with patch.dict("os.environ", {}, clear=True):
                with patch("edison.core.utils.dependencies.detect_uvx") as mock_detect:
                    mock_detect.return_value = UvxStatus(
                        available=False,
                        version=None,
                        path=None,
                        install_instruction="Install uvx"
                    )

                    available, path = detect_zen_mcp_server()

                    assert available is False
                    assert path is None

    def test_detect_zen_mcp_server_env_var_takes_precedence(self, tmp_path):
        """Test: detect_zen_mcp_server prioritizes ZEN_MCP_SERVER_DIR over home directory."""
        # Create both installations
        env_zen = tmp_path / "env-zen"
        env_zen.mkdir()
        (env_zen / "pyproject.toml").write_text("[project]\nname='zen-env'")

        home_zen = tmp_path / "zen-mcp-server"
        home_zen.mkdir()
        (home_zen / "pyproject.toml").write_text("[project]\nname='zen-home'")

        with patch.dict("os.environ", {"ZEN_MCP_SERVER_DIR": str(env_zen)}):
            with patch("pathlib.Path.home", return_value=tmp_path):
                available, path = detect_zen_mcp_server()

                assert available is True
                assert path == env_zen  # Should return env var path, not home

    def test_detect_zen_mcp_server_requires_pyproject_toml(self, tmp_path):
        """Test: detect_zen_mcp_server requires pyproject.toml to be present."""
        zen_dir = tmp_path / "zen-mcp-server"
        zen_dir.mkdir()
        # No pyproject.toml

        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                with patch("edison.core.utils.dependencies.detect_uvx") as mock_detect:
                    mock_detect.return_value = UvxStatus(
                        available=False,
                        version=None,
                        path=None,
                        install_instruction="Install uvx"
                    )

                    available, path = detect_zen_mcp_server()

                    assert available is False
                    assert path is None
