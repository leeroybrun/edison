"""Tests for validator report I/O operations.

NO MOCKS - real config, real files, real behavior.
Note: Validator report filenames follow fixed pattern: validator-{name}-report.json
This is not configurable (yet) unlike bundle/implementation reports.
"""
from __future__ import annotations

from pathlib import Path
import json

from edison.core.qa.evidence import reports


class TestValidatorReports:
    """Test validator report I/O operations."""

    def test_write_validator_report(self, round_dir: Path):
        """Should write validator report with correct naming convention."""
        data = {
            "validator": "security",
            "status": "passed",
            "score": 95,
            "findings": [],
        }

        reports.write_validator_report(round_dir, "security", data)

        report_file = round_dir / "validator-security-report.json"
        assert report_file.exists()

        content = json.loads(report_file.read_text())
        assert content == data

    def test_write_validator_report_with_prefix(self, round_dir: Path):
        """Should handle validator names that already have 'validator-' prefix."""
        data = {"status": "passed"}

        # Pass name with "validator-" prefix - should not duplicate
        reports.write_validator_report(round_dir, "validator-performance", data)

        report_file = round_dir / "validator-performance-report.json"
        assert report_file.exists()

        # Should NOT create "validator-validator-performance-report.json"
        wrong_file = round_dir / "validator-validator-performance-report.json"
        assert not wrong_file.exists()

    def test_read_validator_report(self, round_dir: Path):
        """Should read validator report."""
        data = {"validator": "testing", "score": 100}
        report_file = round_dir / "validator-testing-report.json"
        report_file.write_text(json.dumps(data))

        result = reports.read_validator_report(round_dir, "testing")

        assert result == data

    def test_read_validator_report_with_prefix(self, round_dir: Path):
        """Should handle validator names with 'validator-' prefix."""
        data = {"score": 85}
        report_file = round_dir / "validator-database-report.json"
        report_file.write_text(json.dumps(data))

        result = reports.read_validator_report(round_dir, "validator-database")

        assert result == data

    def test_read_validator_report_missing_file(self, round_dir: Path):
        """Should return empty dict when validator report doesn't exist."""
        result = reports.read_validator_report(round_dir, "nonexistent")

        assert result == {}

    def test_read_validator_report_invalid_json(self, round_dir: Path):
        """Should return empty dict when validator report is invalid JSON."""
        report_file = round_dir / "validator-broken-report.json"
        report_file.write_text("{ invalid json")

        result = reports.read_validator_report(round_dir, "broken")

        assert result == {}

    def test_list_validator_reports_empty(self, round_dir: Path):
        """Should return empty list when no validator reports exist."""
        result = reports.list_validator_reports(round_dir)

        assert result == []

    def test_list_validator_reports_single(self, round_dir: Path):
        """Should list single validator report."""
        (round_dir / "validator-test-report.json").touch()

        result = reports.list_validator_reports(round_dir)

        assert len(result) == 1
        assert result[0].name == "validator-test-report.json"

    def test_list_validator_reports_multiple(self, round_dir: Path):
        """Should list all validator reports sorted."""
        (round_dir / "validator-security-report.json").touch()
        (round_dir / "validator-performance-report.json").touch()
        (round_dir / "validator-database-report.json").touch()

        # Create non-validator files (should be excluded)
        (round_dir / "bundle-approved.json").touch()
        (round_dir / "implementation-report.json").touch()

        result = reports.list_validator_reports(round_dir)

        assert len(result) == 3
        names = [f.name for f in result]
        assert "validator-security-report.json" in names
        assert "validator-performance-report.json" in names
        assert "validator-database-report.json" in names

        # Non-validator files should NOT be included
        assert "bundle-approved.json" not in names
        assert "implementation-report.json" not in names

    def test_list_validator_reports_sorted(self, round_dir: Path):
        """Should return validator reports in sorted order."""
        (round_dir / "validator-zebra-report.json").touch()
        (round_dir / "validator-alpha-report.json").touch()
        (round_dir / "validator-beta-report.json").touch()

        result = reports.list_validator_reports(round_dir)

        names = [f.name for f in result]
        assert names == sorted(names)
