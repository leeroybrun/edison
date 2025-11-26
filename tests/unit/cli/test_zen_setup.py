import subprocess
import sys
from pathlib import Path
import pytest
import os

# Test structure similar to tests/scripts/test_tasks_and_qa_cli.py
def run_zen_setup(args: list[str], env: dict) -> subprocess.CompletedProcess:
    """Execute zen setup command."""
    # Ensure PYTHONPATH includes the src directory so we can find edison
    if "PYTHONPATH" not in env:
        # Assuming the tests are run from project root, src is at ./src
        # But best to be explicit if we can locate it relative to this file?
        # The existing tests likely rely on pytest adding src to path,
        # but subprocess needs it explicitly if we are running a new python process.
        # However, since we are running 'python -m ...', we need 'edison' to be resolvable.
        # Let's assume the environment passed in or inherited covers it, 
        # OR we add current working directory/src to PYTHONPATH.
        # The prompt's example doesn't show explicitly adding PYTHONPATH,
        # but typically in these environments 'src' is in the path.
        # Let's check if we need to add it.
        env["PYTHONPATH"] = os.getcwd() + "/src"
    
    cmd = [sys.executable, "-m", "edison.cli.zen.setup", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        check=False,  # Don't raise on non-zero exit
    )

def test_zen_setup_finds_existing_installation(tmp_path: Path, monkeypatch):
    """Test: Command detects existing zen-mcp-server installation."""
    # Create fake zen installation
    zen_dir = tmp_path / "zen-mcp-server"
    zen_dir.mkdir()
    (zen_dir / "pyproject.toml").write_text("[project]\nname = \"zen\"")
    
    # Set env to point to it
    env = os.environ.copy()
    env["ZEN_MCP_SERVER_DIR"] = str(zen_dir)
    env["PYTHONPATH"] = os.getcwd() + "/src"
    
    result = run_zen_setup([], env)
    # Assert failure details if it fails for debugging
    if result.returncode != 0:
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
    assert result.returncode == 0
    assert "✅ zen-mcp-server found at:" in result.stdout
    assert str(zen_dir) in result.stdout

def test_zen_setup_check_flag_no_uvx(tmp_path: Path, monkeypatch):
    """Test: --check flag reports uvx missing without aborting."""
    env = os.environ.copy()
    # Prepend tmp_path to PATH instead of replacing it
    env["PATH"] = str(tmp_path) + os.pathsep + env.get("PATH", "")
    env.pop("ZEN_MCP_SERVER_DIR", None)
    env["PYTHONPATH"] = os.getcwd() + "/src"

    # Mock HOME to avoid finding real installations
    env["HOME"] = str(tmp_path)

    result = run_zen_setup(["--check"], env)
    # The test might find a real uvx in PATH, so we need to ensure uvx is not in tmp_path
    # But since we prepended tmp_path, shutil.which('uvx') will check tmp_path first
    # However, if uvx exists elsewhere in PATH, it will still be found
    # To properly test "no uvx", we need to ensure uvx is not found at all
    # Let's check if uvx was found in the real PATH
    import shutil
    real_uvx = shutil.which("uvx")
    if real_uvx:
        # Skip this test if uvx is actually installed
        pytest.skip("uvx is installed in the system, cannot test 'no uvx' scenario")

    assert "❌" in result.stdout
    assert result.returncode == 0  # Should succeed with --check

def test_zen_setup_check_flag_with_uvx(tmp_path: Path, monkeypatch):
    """Test: --check flag shows installation message when uvx available."""
    # Create fake uvx script
    fake_uvx = tmp_path / "uvx"
    fake_uvx.write_text("#!/bin/bash\necho 'uvx 0.1.0'")
    fake_uvx.chmod(0o755)

    env = os.environ.copy()
    # Prepend tmp_path to PATH so our fake uvx is found first
    env["PATH"] = str(tmp_path) + os.pathsep + env.get("PATH", "")
    env.pop("ZEN_MCP_SERVER_DIR", None)
    env["HOME"] = str(tmp_path)
    env["PYTHONPATH"] = os.getcwd() + "/src"

    result = run_zen_setup(["--check"], env)
    assert result.returncode == 0
    assert "ℹ️" in result.stdout
    assert "zen-mcp-server will be installed via uvx on first use" in result.stdout

def test_zen_setup_no_uvx_aborts_without_check(tmp_path: Path):
    """Test: Missing uvx causes abort when not using --check."""
    env = os.environ.copy()
    # Prepend tmp_path to PATH instead of replacing it
    env["PATH"] = str(tmp_path) + os.pathsep + env.get("PATH", "")
    env.pop("ZEN_MCP_SERVER_DIR", None)
    env["HOME"] = str(tmp_path)
    env["PYTHONPATH"] = os.getcwd() + "/src"

    # Check if uvx is actually installed in the system
    import shutil
    real_uvx = shutil.which("uvx")
    if real_uvx:
        # Skip this test if uvx is actually installed
        pytest.skip("uvx is installed in the system, cannot test 'no uvx' scenario")

    result = run_zen_setup([], env)
    assert result.returncode != 0
    assert "❌" in result.stdout
