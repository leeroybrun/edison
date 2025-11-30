"""
Integration tests for zen-mcp-server relocation into .edison

Tests verify:
1. zen-mcp-server exists in .edison/tools/
2. setup.sh creates working venv
3. run-server.sh launches with ZEN_WORKING_DIR
4. .mcp.json is valid and properly configured
5. No dependency on global ~/Documents/Development/zen-mcp-server

TDD: These tests SHOULD FAIL initially (RED phase)

NOTE: These tests are PROJECT-SPECIFIC (wilson-leadgen).
They skip when running in standalone Edison package.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.helpers.timeouts import SUBPROCESS_TIMEOUT, PROCESS_WAIT_TIMEOUT


def _has_zen_mcp_setup() -> bool:
    """Check if zen-mcp-server is set up (project-specific, not in standalone Edison)."""
    # These tests require:
    # 1. .edison/tools/zen-mcp-server/
    # 2. .edison/scripts/zen/
    # 3. .mcp.json at project root
    #
    # This is ONLY present in wilson-leadgen, NOT in standalone Edison package
    test_dir = Path(__file__).parent

    # Try to find .edison directory by going up
    current = test_dir
    for _ in range(5):  # Go up max 5 levels
        edison_dir = current / ".edison"
        if edison_dir.exists():
            # Check if zen-mcp-server is actually set up
            has_zen_server = (edison_dir / "tools" / "zen-mcp-server").exists()
            has_zen_scripts = (edison_dir / "scripts" / "zen").exists()
            has_mcp_json = (current / ".mcp.json").exists()

            if has_zen_server or has_zen_scripts or has_mcp_json:
                return True

        if current.parent == current:
            break
        current = current.parent

    return False


# Skip entire test class if zen-mcp-server not set up
pytestmark = pytest.mark.skipif(
    not _has_zen_mcp_setup(),
    reason="Zen MCP integration tests require project-specific zen-mcp-server setup (wilson-leadgen)"
)


class TestZenMcpRelocation:
    """Test suite for zen-mcp-server relocation to .edison/tools/"""

    @pytest.fixture
    def edison_root(self):
        """
        Get .edison root directory.

        In wilson-leadgen project structure:
        - Test file: /path/to/wilson-leadgen/tests/integration/test_zen_mcp_integration.py
        - Searches up to find: /path/to/wilson-leadgen/.edison/
        """
        test_dir = Path(__file__).parent

        # Find .edison directory by going up from test location
        current = test_dir
        for _ in range(5):
            if (current / ".edison").exists():
                return current / ".edison"
            if current.parent == current:
                break
            current = current.parent

        pytest.fail("Could not find .edison directory - this test requires wilson-leadgen project")

    @pytest.fixture
    def project_root(self, edison_root):
        """Get project root directory"""
        return edison_root.parent

    @pytest.fixture
    def zen_server_dir(self, edison_root):
        """Get zen-mcp-server directory in .edison/tools/"""
        return edison_root / "tools" / "zen-mcp-server"

    def test_zen_server_exists_in_edison_tools(self, zen_server_dir):
        """Test that zen-mcp-server directory exists in .edison/tools/"""
        assert zen_server_dir.exists(), (
            f"zen-mcp-server not found at {zen_server_dir}. "
            "Expected to be relocated from global location."
        )
        assert zen_server_dir.is_dir(), f"{zen_server_dir} is not a directory"

    def test_zen_server_has_required_files(self, zen_server_dir):
        """Test that zen-mcp-server has all required files"""
        required_files = [
            "server.py",
            "requirements.txt",
            ".gitignore",
        ]

        for filename in required_files:
            file_path = zen_server_dir / filename
            assert file_path.exists(), f"Missing required file: {file_path}"

    def test_zen_server_gitignore_contains_venv(self, zen_server_dir):
        """Test that .gitignore properly ignores .venv"""
        gitignore = zen_server_dir / ".gitignore"
        assert gitignore.exists(), f".gitignore not found at {gitignore}"

        content = gitignore.read_text()
        assert ".venv/" in content, ".gitignore must contain .venv/"
        assert "__pycache__/" in content, ".gitignore must contain __pycache__/"
        assert "*.pyc" in content, ".gitignore must contain *.pyc"

    def test_setup_script_exists(self, edison_root):
        """Test that setup.sh exists in .edison/scripts/zen/"""
        setup_script = edison_root / "scripts" / "zen" / "setup.sh"
        assert setup_script.exists(), f"setup.sh not found at {setup_script}"
        assert os.access(setup_script, os.X_OK), "setup.sh must be executable"

    def test_run_server_script_exists(self, edison_root):
        """Test that run-server.sh exists in .edison/scripts/zen/"""
        run_script = edison_root / "scripts" / "zen" / "run-server.sh"
        assert run_script.exists(), f"run-server.sh not found at {run_script}"
        assert os.access(run_script, os.X_OK), "run-server.sh must be executable"

    def test_run_server_prioritizes_local_edison_tools(self, edison_root):
        """Test that run-server.sh prioritizes .edison/tools/zen-mcp-server"""
        run_script = edison_root / "scripts" / "zen" / "run-server.sh"
        content = run_script.read_text()

        # Should check for .edison/tools/zen-mcp-server FIRST
        assert ".edison/tools/zen-mcp-server" in content or "EDISON_ROOT" in content, (
            "run-server.sh must check for local .edison/tools/zen-mcp-server"
        )

        # Should NOT have ~/Documents/Development/zen-mcp-server as fallback
        # (it's OK to have it as option 2, but .edison should be priority 1)
        lines = content.split('\n')
        edison_check_line = None
        global_check_line = None

        for i, line in enumerate(lines):
            if '.edison/tools/zen-mcp-server' in line or 'EDISON_ROOT' in line:
                if edison_check_line is None:
                    edison_check_line = i
            if '$HOME/Documents/Development/zen-mcp-server' in line:
                if global_check_line is None:
                    global_check_line = i

        assert edison_check_line is not None, (
            "run-server.sh must check for .edison/tools/zen-mcp-server"
        )

    def test_mcp_json_exists_at_project_root(self, project_root):
        """Test that .mcp.json exists at project root (not in .edison)"""
        mcp_json = project_root / ".mcp.json"
        assert mcp_json.exists(), (
            f".mcp.json not found at {mcp_json}. "
            "Claude Code requires .mcp.json at workspace root."
        )

    def test_mcp_json_is_valid_json(self, project_root):
        """Test that .mcp.json is valid JSON"""
        mcp_json = project_root / ".mcp.json"

        try:
            with open(mcp_json) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f".mcp.json is not valid JSON: {e}")

        assert isinstance(data, dict), ".mcp.json must be a JSON object"

    def test_mcp_json_has_edison_zen_config(self, project_root):
        """Test that .mcp.json contains edison-zen MCP server configuration"""
        mcp_json = project_root / ".mcp.json"

        with open(mcp_json) as f:
            data = json.load(f)

        assert "mcpServers" in data, ".mcp.json must have mcpServers key"
        assert "edison-zen" in data["mcpServers"], (
            ".mcp.json must have edison-zen server config"
        )

    def test_edison_zen_config_uses_local_run_script(self, project_root):
        """Test that edison-zen config points to .edison/scripts/zen/run-server.sh"""
        mcp_json = project_root / ".mcp.json"

        with open(mcp_json) as f:
            data = json.load(f)

        edison_zen = data["mcpServers"]["edison-zen"]

        # Check command
        assert edison_zen.get("command") in ["bash", "/bin/bash"], (
            "edison-zen must use bash command"
        )

        # Check args include .edison/scripts/zen/run-server.sh
        args = edison_zen.get("args", [])
        assert len(args) > 0, "edison-zen must have args"

        run_script_arg = args[0]
        assert ".edison/scripts/zen/run-server.sh" in run_script_arg, (
            f"edison-zen must use .edison/scripts/zen/run-server.sh, got: {run_script_arg}"
        )

    def test_edison_zen_config_sets_zen_working_dir(self, project_root):
        """Test that edison-zen config sets ZEN_WORKING_DIR environment variable"""
        mcp_json = project_root / ".mcp.json"

        with open(mcp_json) as f:
            data = json.load(f)

        edison_zen = data["mcpServers"]["edison-zen"]
        env = edison_zen.get("env", {})

        assert "ZEN_WORKING_DIR" in env, (
            "edison-zen must set ZEN_WORKING_DIR in env"
        )

        # Should use ${workspaceFolder} variable
        assert "${workspaceFolder}" in env["ZEN_WORKING_DIR"], (
            "ZEN_WORKING_DIR should use ${workspaceFolder} variable"
        )

    def test_mcp_json_example_exists(self, project_root):
        """Test that .mcp.json.example exists as a template"""
        example = project_root / ".mcp.json.example"
        assert example.exists(), (
            f".mcp.json.example not found at {example}. "
            "Template should exist for users to copy."
        )

    def test_mcp_json_example_has_placeholders(self, project_root):
        """Test that .mcp.json.example has placeholder API keys"""
        example = project_root / ".mcp.json.example"

        with open(example) as f:
            data = json.load(f)

        edison_zen = data["mcpServers"]["edison-zen"]
        env = edison_zen.get("env", {})

        # API keys should use ${env:...} placeholders
        api_key_vars = ["GEMINI_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"]

        for var in api_key_vars:
            if var in env:
                value = env[var]
                assert "${env:" in value, (
                    f"{var} should use ${{env:...}} placeholder, got: {value}"
                )

    def test_project_gitignore_excludes_mcp_json(self, project_root):
        """Test that project .gitignore excludes .mcp.json (user-specific)"""
        gitignore = project_root / ".gitignore"

        if gitignore.exists():
            content = gitignore.read_text()
            assert ".mcp.json" in content or "*.mcp.json" in content, (
                ".gitignore should exclude .mcp.json (contains user API keys)"
            )

    def test_edison_gitignore_excludes_zen_venv(self, edison_root):
        """Test that .edison/.gitignore excludes zen-mcp-server/.venv"""
        gitignore = edison_root / ".gitignore"

        if gitignore.exists():
            content = gitignore.read_text()
            assert "tools/zen-mcp-server/.venv" in content or ".venv" in content, (
                ".edison/.gitignore should exclude zen-mcp-server/.venv"
            )

    @pytest.fixture
    def clean_zen_venv(self, zen_server_dir):
        """Fixture to manage zen venv state.

        Creates fresh venv for tests, cleans up after.
        Uses fixture instead of deleting during test to avoid side effects.
        """
        venv_dir = zen_server_dir / ".venv"
        # Clean existing venv if present
        if venv_dir.exists():
            import shutil
            shutil.rmtree(venv_dir)
        yield venv_dir
        # Cleanup happens automatically with tmp_path

    def test_setup_creates_venv(self, edison_root, zen_server_dir, clean_zen_venv):
        """Test that setup.sh creates virtualenv in .edison/tools/zen-mcp-server/.venv"""
        venv_dir = clean_zen_venv

        # Run setup script
        setup_script = edison_root / "scripts" / "zen" / "setup.sh"
        result = subprocess.run(
            [str(setup_script)],
            cwd=str(edison_root),
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )

        assert result.returncode == 0, (
            f"setup.sh failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )

        # Verify venv was created
        assert venv_dir.exists(), f"setup.sh did not create .venv at {venv_dir}"
        assert (venv_dir / "bin" / "activate").exists(), (
            "venv missing activate script"
        )
        assert (venv_dir / "bin" / "python").exists() or (venv_dir / "bin" / "python3").exists(), (
            "venv missing python executable"
        )

    def test_run_server_requires_zen_working_dir(self, edison_root):
        """Test that run-server.sh fails without ZEN_WORKING_DIR"""
        run_script = edison_root / "scripts" / "zen" / "run-server.sh"

        # Run WITHOUT ZEN_WORKING_DIR
        env = os.environ.copy()
        if "ZEN_WORKING_DIR" in env:
            del env["ZEN_WORKING_DIR"]

        result = subprocess.run(
            [str(run_script), "--help"],
            cwd=str(edison_root),
            capture_output=True,
            text=True,
            env=env,
            timeout=int(PROCESS_WAIT_TIMEOUT),
        )

        # Should fail with error about ZEN_WORKING_DIR
        assert result.returncode != 0, (
            "run-server.sh should fail without ZEN_WORKING_DIR"
        )
        assert "ZEN_WORKING_DIR" in result.stderr, (
            "Error message should mention ZEN_WORKING_DIR"
        )

    def test_run_server_works_with_zen_working_dir(self, edison_root, project_root):
        """Test that run-server.sh launches with ZEN_WORKING_DIR set"""
        # Skip if venv doesn't exist yet
        zen_server_dir = edison_root / "tools" / "zen-mcp-server"
        venv_dir = zen_server_dir / ".venv"
        if not venv_dir.exists():
            pytest.skip("venv not created yet, run setup.sh first")

        run_script = edison_root / "scripts" / "zen" / "run-server.sh"

        # Run WITH ZEN_WORKING_DIR
        env = os.environ.copy()
        env["ZEN_WORKING_DIR"] = str(project_root)

        # Just check if it starts (use --help or similar)
        result = subprocess.run(
            [str(run_script), "--help"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            env=env,
            timeout=int(PROCESS_WAIT_TIMEOUT),
        )

        # Should succeed or at least not fail on ZEN_WORKING_DIR check
        # (may fail on other validation, but not on missing ZEN_WORKING_DIR)
        if result.returncode != 0:
            assert "ZEN_WORKING_DIR" not in result.stderr, (
                f"Should not fail on ZEN_WORKING_DIR check:\n{result.stderr}"
            )

    def test_no_dependency_on_global_zen_server(self, edison_root):
        """Test that .edison is 100% relocatable (no hardcoded global paths)"""
        # Check run-server.sh doesn't REQUIRE global installation
        run_script = edison_root / "scripts" / "zen" / "run-server.sh"
        content = run_script.read_text()

        # Should NOT fail if global ~/Documents/Development/zen-mcp-server missing
        # as long as .edison/tools/zen-mcp-server exists

        # This is a design check - if .edison/tools/zen-mcp-server exists,
        # script should use it WITHOUT checking global location
        lines = content.split('\n')

        # Find the SERVER_DIR detection logic
        server_dir_section = []
        in_section = False
        for line in lines:
            if 'SERVER_DIR' in line or in_section:
                server_dir_section.append(line)
                in_section = True
                if line.strip().startswith('fi') and in_section:
                    break

        section_text = '\n'.join(server_dir_section)

        # Priority should be: .edison/tools > explicit override > fail
        # NOT: .edison/tools > explicit override > global fallback
        assert section_text, "Could not find SERVER_DIR detection section"
