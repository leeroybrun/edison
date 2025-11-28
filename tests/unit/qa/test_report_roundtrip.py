"""Tests for write-then-read roundtrip operations.

NO MOCKS - real config, real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.qa.evidence import reports


class TestRoundtrip:
    """Test write-then-read roundtrip operations."""

    def test_bundle_report_roundtrip(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should successfully roundtrip bundle report data."""
        original_data = {
            "status": "approved",
            "timestamp": "2025-01-01T12:00:00Z",
            "validators": ["security", "performance"],
            "score": 95,
            "notes": "All checks passed",
        }

        # Write
        reports.write_bundle_report(
            round_dir, original_data, repo_root=isolated_project_env
        )

        # Read
        loaded_data = reports.read_bundle_report(
            round_dir, repo_root=isolated_project_env
        )

        assert loaded_data == original_data

    def test_implementation_report_roundtrip(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should successfully roundtrip implementation report data."""
        original_data = {
            "files": ["src/feature.py", "src/utils.py"],
            "tests": ["tests/test_feature.py"],
            "summary": "Implemented new feature with tests",
            "lines_added": 150,
            "lines_removed": 20,
        }

        # Write
        reports.write_implementation_report(
            round_dir, original_data, repo_root=isolated_project_env
        )

        # Read
        loaded_data = reports.read_implementation_report(
            round_dir, repo_root=isolated_project_env
        )

        assert loaded_data == original_data

    def test_validator_report_roundtrip(self, round_dir: Path):
        """Should successfully roundtrip validator report data."""
        original_data = {
            "validator": "security",
            "status": "passed",
            "score": 98,
            "findings": [
                {"type": "info", "message": "All security checks passed"}
            ],
            "execution_time_ms": 1234,
        }

        # Write
        reports.write_validator_report(round_dir, "security", original_data)

        # Read
        loaded_data = reports.read_validator_report(round_dir, "security")

        assert loaded_data == original_data
