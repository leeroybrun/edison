"""Tests for implementation report I/O operations.

NO MOCKS - real config, real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path
import json

from edison.core.qa.evidence import reports


class TestImplementationReport:
    """Test implementation report I/O operations."""

    def test_write_implementation_report_default_filename(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should write implementation report with default filename."""
        data = {
            "files": ["src/test.py"],
            "summary": "Implemented feature X",
            "tests": ["tests/test_x.py"],
        }

        reports.write_implementation_report(round_dir, data, repo_root=isolated_project_env)

        report_file = round_dir / "implementation-report.json"
        assert report_file.exists()

        content = json.loads(report_file.read_text())
        assert content == data

    def test_write_implementation_report_custom_filename(
        self, isolated_qa_config: Path, round_dir: Path
    ):
        """Should write implementation report with custom filename from config."""
        data = {"files": ["main.py"]}

        reports.write_implementation_report(round_dir, data, repo_root=isolated_qa_config)

        report_file = round_dir / "custom-impl.json"
        assert report_file.exists()

        content = json.loads(report_file.read_text())
        assert content == data

    def test_read_implementation_report_default_filename(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should read implementation report with default filename."""
        data = {"files": ["a.py", "b.py"], "summary": "test"}
        report_file = round_dir / "implementation-report.json"
        report_file.write_text(json.dumps(data))

        result = reports.read_implementation_report(round_dir, repo_root=isolated_project_env)

        assert result == data

    def test_read_implementation_report_custom_filename(
        self, isolated_qa_config: Path, round_dir: Path
    ):
        """Should read implementation report with custom filename from config."""
        data = {"summary": "custom implementation"}
        report_file = round_dir / "custom-impl.json"
        report_file.write_text(json.dumps(data))

        result = reports.read_implementation_report(round_dir, repo_root=isolated_qa_config)

        assert result == data

    def test_read_implementation_report_missing_file(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should return empty dict when implementation report doesn't exist."""
        result = reports.read_implementation_report(round_dir, repo_root=isolated_project_env)

        assert result == {}

    def test_read_implementation_report_invalid_json(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should return empty dict when implementation report is invalid JSON."""
        report_file = round_dir / "implementation-report.json"
        report_file.write_text("invalid json")

        result = reports.read_implementation_report(round_dir, repo_root=isolated_project_env)

        assert result == {}
