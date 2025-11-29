"""Tests for bundle report I/O operations.

NO MOCKS - real config, real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path
import json

from edison.core.qa.evidence import reports


class TestBundleReport:
    """Test bundle report I/O operations."""

    def test_write_bundle_report_default_filename(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should write bundle report with default filename."""
        data = {
            "status": "approved",
            "timestamp": "2025-01-01T00:00:00Z",
            "validators": ["test-validator"],
        }

        reports.write_bundle_report(round_dir, data, repo_root=isolated_project_env)

        # Should create file with default name
        bundle_file = round_dir / "bundle-approved.json"
        assert bundle_file.exists()

        # Verify content
        content = json.loads(bundle_file.read_text())
        assert content == data

    def test_write_bundle_report_custom_filename(
        self, isolated_qa_config: Path, round_dir: Path
    ):
        """Should write bundle report with custom filename from config."""
        data = {"status": "pending"}

        reports.write_bundle_report(round_dir, data, repo_root=isolated_qa_config)

        # Should use custom filename from config
        bundle_file = round_dir / "custom-bundle.json"
        assert bundle_file.exists()

        content = json.loads(bundle_file.read_text())
        assert content == data

    def test_read_bundle_report_default_filename(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should read bundle report with default filename."""
        data = {"status": "approved", "score": 100}
        bundle_file = round_dir / "bundle-approved.json"
        bundle_file.write_text(json.dumps(data))

        result = reports.read_bundle_report(round_dir, repo_root=isolated_project_env)

        assert result == data

    def test_read_bundle_report_custom_filename(
        self, isolated_qa_config: Path, round_dir: Path
    ):
        """Should read bundle report with custom filename from config."""
        data = {"status": "failed", "errors": ["test error"]}
        bundle_file = round_dir / "custom-bundle.json"
        bundle_file.write_text(json.dumps(data))

        result = reports.read_bundle_report(round_dir, repo_root=isolated_qa_config)

        assert result == data

    def test_read_bundle_report_missing_file(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should return empty dict when bundle report doesn't exist."""
        result = reports.read_bundle_report(round_dir, repo_root=isolated_project_env)

        assert result == {}

    def test_read_bundle_report_invalid_json(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should return empty dict when bundle report is invalid JSON."""
        bundle_file = round_dir / "bundle-approved.json"
        bundle_file.write_text("not valid json {")

        result = reports.read_bundle_report(round_dir, repo_root=isolated_project_env)

        assert result == {}
