import subprocess
import sys
from pathlib import Path
import pytest
import os


def run_zen_start_server(args: list[str], env: dict) -> subprocess.CompletedProcess:
    """Execute zen start-server command."""
    if "PYTHONPATH" not in env:
        env["PYTHONPATH"] = os.getcwd() + "/src"

    # Use importlib to import the module with hyphenated name
    cmd = [sys.executable, "-c",
           "import sys; sys.path.insert(0, 'src'); "
           "import importlib; "
           "mod = importlib.import_module('edison.cli.zen.start-server'); "
           "import argparse; p = argparse.ArgumentParser(); "
           "mod.register_args(p); sys.exit(mod.main(p.parse_args(sys.argv[1:])))",
           *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        check=False,  # Don't raise on non-zero exit
    )


def test_start_server_uses_run_server_script_when_available(tmp_path: Path):
    """Test: Command uses run-server.sh when available."""
    # Create fake run-server.sh in expected location
    # The script is located at src/scripts/zen/run-server.sh relative to the zen module
    # We need to mock this by setting up the environment

    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + "/src"

    # Create a marker file to track if script was called
    marker_file = tmp_path / "script_was_called"

    # Create fake run-server.sh that creates the marker
    fake_script = tmp_path / "run-server.sh"
    fake_script.write_text(f"#!/bin/bash\ntouch {marker_file}\n")
    fake_script.chmod(0o755)

    # Mock the script path by setting an env var that the command will use
    env["ZEN_RUN_SERVER_SCRIPT"] = str(fake_script)

    result = run_zen_start_server([], env)

    # Should succeed
    assert result.returncode == 0
    # Marker file should exist if script was called
    assert marker_file.exists()


def test_start_server_fallback_to_uvx_when_no_script(tmp_path: Path):
    """Test: Command falls back to uvx when run-server.sh is missing."""
    # Create fake uvx that accepts arguments and exits successfully
    fake_uvx = tmp_path / "uvx"
    marker_file = tmp_path / "uvx_was_called"
    # Accept all arguments ($@) to simulate real uvx - use /usr/bin/touch for full path
    fake_uvx.write_text(f"#!/bin/bash\n/usr/bin/touch {marker_file}\nexit 0\n")
    fake_uvx.chmod(0o755)

    env = os.environ.copy()
    # Prepend tmp_path to PATH so our fake uvx is found first
    env["PATH"] = str(tmp_path) + ":" + env.get("PATH", "")
    env["PYTHONPATH"] = os.getcwd() + "/src"
    # Ensure no script is found
    env["ZEN_RUN_SERVER_SCRIPT"] = "/nonexistent/path/run-server.sh"

    result = run_zen_start_server([], env)

    # Should succeed
    assert result.returncode == 0
    # uvx should have been called
    assert marker_file.exists()


def test_start_server_background_flag(tmp_path: Path):
    """Test: --background flag runs server in background."""
    # Create fake script that writes to a file
    fake_script = tmp_path / "run-server.sh"
    output_file = tmp_path / "output.txt"
    fake_script.write_text(f"#!/bin/bash\necho 'running' > {output_file}\n")
    fake_script.chmod(0o755)

    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd() + "/src"
    env["ZEN_RUN_SERVER_SCRIPT"] = str(fake_script)

    result = run_zen_start_server(["--background"], env)

    # Should succeed and return immediately (not wait for process)
    assert result.returncode == 0


def test_start_server_no_uvx_fails_gracefully(tmp_path: Path):
    """Test: Missing uvx and script fails with helpful message."""
    env = os.environ.copy()
    env["PATH"] = str(tmp_path)  # Empty PATH, no uvx
    env["PYTHONPATH"] = os.getcwd() + "/src"
    env["ZEN_RUN_SERVER_SCRIPT"] = "/nonexistent/path/run-server.sh"

    result = run_zen_start_server([], env)

    # Should fail
    assert result.returncode != 0
    # Should have helpful error message
    assert "uvx" in result.stderr or "uvx" in result.stdout


def test_start_server_command_module_exists():
    """Test: Command module can be imported."""
    try:
        import importlib
        mod = importlib.import_module('edison.cli.zen.start-server')
        assert hasattr(mod, 'main')
        assert hasattr(mod, 'register_args')
        assert hasattr(mod, 'SUMMARY')
    except ImportError as e:
        pytest.fail(f"Failed to import edison.cli.zen.start-server: {e}")
