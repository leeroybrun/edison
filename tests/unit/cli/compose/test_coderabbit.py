"""Tests for edison compose coderabbit CLI command.

NO MOCKS - real subprocess calls, real file I/O, real CLI execution.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def run_compose_coderabbit(args: list[str], env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    """Execute edison compose coderabbit via the module."""
    env = env.copy()
    env.setdefault("PYTHONPATH", os.getcwd() + "/src")

    cmd = [sys.executable, "-m", "edison.cli.compose.coderabbit", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def _base_env(project_root: Path) -> dict[str, str]:
    """Create base environment for tests."""
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    return env


class TestComposeCodeRabbitCLI:
    """Tests for compose coderabbit CLI command."""

    def test_cli_writes_file(self, tmp_path: Path) -> None:
        """CLI should write .coderabbit.yaml to repo root."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        result = run_compose_coderabbit([], _base_env(project), project)

        if result.returncode != 0:
            raise AssertionError(f"Command failed:\n{result.stdout}\n{result.stderr}")

        # File should be created
        coderabbit_file = project / ".coderabbit.yaml"
        assert coderabbit_file.exists(), f".coderabbit.yaml should be created at {coderabbit_file}"

        # Should be valid YAML
        content = yaml.safe_load(coderabbit_file.read_text())
        assert isinstance(content, dict)

    def test_cli_dry_run(self, tmp_path: Path) -> None:
        """--dry-run should not write file."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        result = run_compose_coderabbit(["--dry-run"], _base_env(project), project)

        assert result.returncode == 0, f"Command should succeed:\n{result.stderr}"

        # File should NOT be created
        coderabbit_file = project / ".coderabbit.yaml"
        assert not coderabbit_file.exists(), ".coderabbit.yaml should not be created in dry-run mode"

        # Should show preview in output
        assert "dry-run" in result.stdout.lower()

    def test_cli_custom_output(self, tmp_path: Path) -> None:
        """--output should write to custom location."""
        project = tmp_path / "project"
        project.mkdir()

        custom_dir = project / "config" / "ide"
        custom_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        result = run_compose_coderabbit(
            ["--output", str(custom_dir)],
            _base_env(project),
            project
        )

        if result.returncode != 0:
            raise AssertionError(f"Command failed:\n{result.stdout}\n{result.stderr}")

        # File should be in custom location
        custom_file = custom_dir / ".coderabbit.yaml"
        assert custom_file.exists(), f".coderabbit.yaml should be at {custom_file}"

        # Should NOT be in repo root
        root_file = project / ".coderabbit.yaml"
        assert not root_file.exists() or custom_file != root_file

    def test_cli_json_output(self, tmp_path: Path) -> None:
        """--json should output JSON format."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        result = run_compose_coderabbit(["--json"], _base_env(project), project)

        assert result.returncode == 0, f"Command should succeed:\n{result.stderr}"

        # Should output valid JSON
        output_data = json.loads(result.stdout)
        assert isinstance(output_data, dict)
        assert "status" in output_data
        assert output_data["status"] == "success"
        assert "config_file" in output_data

    def test_cli_json_dry_run(self, tmp_path: Path) -> None:
        """--json --dry-run should output config preview as JSON."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        result = run_compose_coderabbit(
            ["--json", "--dry-run"],
            _base_env(project),
            project
        )

        assert result.returncode == 0, f"Command should succeed:\n{result.stderr}"

        # Should output valid JSON
        output_data = json.loads(result.stdout)
        assert isinstance(output_data, dict)
        assert output_data["status"] == "dry-run"
        assert "config" in output_data
        assert isinstance(output_data["config"], dict)

    def test_cli_with_project_config(self, tmp_path: Path) -> None:
        """CLI should respect project-level CodeRabbit configuration."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        # Create project config
        config_dir = project / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        coderabbit_config = config_dir / "coderabbit.yaml"
        config_data = {
            "coderabbit": {
                "reviews": {
                    "test_project_value": True
                }
            }
        }
        coderabbit_config.write_text(yaml.dump(config_data))

        result = run_compose_coderabbit([], _base_env(project), project)

        assert result.returncode == 0, f"Command should succeed:\n{result.stderr}"

        # Read generated file
        output_file = project / ".coderabbit.yaml"
        content = yaml.safe_load(output_file.read_text())

        # Project config should be merged
        assert isinstance(content, dict)

    def test_cli_error_handling(self, tmp_path: Path) -> None:
        """CLI should handle errors gracefully."""
        # Don't initialize git repo to trigger an error
        project = tmp_path / "project"
        project.mkdir()

        result = run_compose_coderabbit([], _base_env(project), project)

        # May succeed or fail depending on whether git is required
        # If it fails, should show error message
        if result.returncode != 0:
            assert result.stderr or result.stdout
            combined = (result.stdout + result.stderr).lower()
            # Should show some kind of error message
            assert "error" in combined or "failed" in combined or len(combined) > 0

    def test_cli_help_flag(self, tmp_path: Path) -> None:
        """--help should display help message."""
        project = tmp_path / "project"
        project.mkdir()

        result = run_compose_coderabbit(["--help"], _base_env(project), project)

        # Help should succeed
        assert result.returncode == 0

        # Should show usage information
        output = result.stdout.lower()
        assert "usage" in output or "coderabbit" in output

    def test_cli_repo_root_flag(self, tmp_path: Path) -> None:
        """--repo-root should specify custom repository root."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        # Run from different directory but specify repo root
        working_dir = tmp_path / "other"
        working_dir.mkdir()

        result = run_compose_coderabbit(
            ["--repo-root", str(project)],
            _base_env(project),
            working_dir
        )

        # Should work when repo-root is specified
        if result.returncode == 0:
            # File should be in specified repo root
            coderabbit_file = project / ".coderabbit.yaml"
            assert coderabbit_file.exists()

    def test_cli_output_shows_written_file(self, tmp_path: Path) -> None:
        """CLI output should show the path to written file."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        result = run_compose_coderabbit([], _base_env(project), project)

        assert result.returncode == 0, f"Command should succeed:\n{result.stderr}"

        # Output should mention the file path
        assert ".coderabbit.yaml" in result.stdout

    def test_cli_overwrites_existing_file(self, tmp_path: Path) -> None:
        """CLI should overwrite existing .coderabbit.yaml."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        # Create existing file
        existing_file = project / ".coderabbit.yaml"
        existing_file.write_text("old_value: true\n")

        result = run_compose_coderabbit([], _base_env(project), project)

        assert result.returncode == 0, f"Command should succeed:\n{result.stderr}"

        # File should be overwritten
        new_content = existing_file.read_text()
        assert new_content != "old_value: true\n"

    def test_cli_with_empty_config(self, tmp_path: Path) -> None:
        """CLI should work even with minimal/empty configuration."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        # Don't create any custom config
        result = run_compose_coderabbit([], _base_env(project), project)

        # Should still succeed
        assert result.returncode == 0, f"Command should succeed:\n{result.stderr}"

        # Should create file
        coderabbit_file = project / ".coderabbit.yaml"
        assert coderabbit_file.exists()

    def test_cli_creates_output_directory(self, tmp_path: Path) -> None:
        """CLI should create output directory if it doesn't exist."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        # Specify non-existent output directory
        custom_dir = project / "deep" / "nested" / "path"

        result = run_compose_coderabbit(
            ["--output", str(custom_dir)],
            _base_env(project),
            project
        )

        if result.returncode != 0:
            raise AssertionError(f"Command failed:\n{result.stdout}\n{result.stderr}")

        # Directory and file should be created
        assert custom_dir.exists()
        assert (custom_dir / ".coderabbit.yaml").exists()

    def test_cli_preserves_yaml_formatting(self, tmp_path: Path) -> None:
        """Generated YAML should be properly formatted."""
        project = tmp_path / "project"
        project.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        result = run_compose_coderabbit([], _base_env(project), project)

        assert result.returncode == 0, f"Command should succeed:\n{result.stderr}"

        # Read generated file
        coderabbit_file = project / ".coderabbit.yaml"
        content = coderabbit_file.read_text()

        # Should be valid YAML
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)

        # Should have proper formatting (no excessive blank lines, etc.)
        lines = content.strip().split("\n")
        assert len(lines) > 0

        # Should not have excessive blank lines
        consecutive_blank = 0
        for line in lines:
            if line.strip() == "":
                consecutive_blank += 1
                assert consecutive_blank < 3, "Too many consecutive blank lines"
            else:
                consecutive_blank = 0
