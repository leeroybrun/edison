"""Tests for validator report I/O operations.

NO MOCKS - real config, real files, real behavior.
Note: Validator report filenames follow fixed pattern: validator-{name}-report.md
"""
from __future__ import annotations

from pathlib import Path

from edison.core.qa.evidence import reports
from edison.core.utils.text import format_frontmatter


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

        report_file = round_dir / "validator-security-report.md"
        assert report_file.exists()

        loaded = reports.read_validator_report(round_dir, "security")
        assert loaded == data

    def test_write_validator_report_with_prefix(self, round_dir: Path):
        """Should handle validator names that already have 'validator-' prefix."""
        data = {"status": "passed"}

        # Pass name with "validator-" prefix - should not duplicate
        reports.write_validator_report(round_dir, "validator-performance", data)

        report_file = round_dir / "validator-performance-report.md"
        assert report_file.exists()

        # Should NOT create "validator-validator-performance-report.md"
        wrong_file = round_dir / "validator-validator-performance-report.md"
        assert not wrong_file.exists()

    def test_read_validator_report(self, round_dir: Path):
        """Should read validator report."""
        data = {"validator": "testing", "score": 100}
        report_file = round_dir / "validator-testing-report.md"
        report_file.write_text(format_frontmatter(data) + "\n# Validator Report\n", encoding="utf-8")

        result = reports.read_validator_report(round_dir, "testing")

        assert result == data

    def test_read_validator_report_with_prefix(self, round_dir: Path):
        """Should handle validator names with 'validator-' prefix."""
        data = {"score": 85}
        report_file = round_dir / "validator-database-report.md"
        report_file.write_text(format_frontmatter(data), encoding="utf-8")

        result = reports.read_validator_report(round_dir, "validator-database")

        assert result == data

    def test_read_validator_report_missing_file(self, round_dir: Path):
        """Should return empty dict when validator report doesn't exist."""
        result = reports.read_validator_report(round_dir, "nonexistent")

        assert result == {}

    def test_read_validator_report_ignores_non_markdown(self, round_dir: Path):
        """Should ignore non-Markdown validator report files."""
        report_file = round_dir / "validator-broken-report.json"
        report_file.write_text("{\"verdict\":\"approve\"}\n", encoding="utf-8")
        assert reports.read_validator_report(round_dir, "broken") == {}

    def test_list_validator_reports_empty(self, round_dir: Path):
        """Should return empty list when no validator reports exist."""
        result = reports.list_validator_reports(round_dir)

        assert result == []

    def test_list_validator_reports_single(self, round_dir: Path):
        """Should list single validator report."""
        (round_dir / "validator-test-report.md").touch()

        result = reports.list_validator_reports(round_dir)

        assert len(result) == 1
        assert result[0].name == "validator-test-report.md"

    def test_list_validator_reports_multiple(self, round_dir: Path):
        """Should list all validator reports sorted."""
        (round_dir / "validator-security-report.md").touch()
        (round_dir / "validator-performance-report.md").touch()
        (round_dir / "validator-database-report.md").touch()

        # Create non-validator files (should be excluded)
        (round_dir / "bundle-approved.md").touch()
        (round_dir / "implementation-report.md").touch()

        result = reports.list_validator_reports(round_dir)

        assert len(result) == 3
        names = [f.name for f in result]
        assert "validator-security-report.md" in names
        assert "validator-performance-report.md" in names
        assert "validator-database-report.md" in names

        # Non-validator files should NOT be included
        assert "bundle-approved.md" not in names
        assert "implementation-report.md" not in names

    def test_list_validator_reports_sorted(self, round_dir: Path):
        """Should return validator reports in sorted order."""
        (round_dir / "validator-zebra-report.md").touch()
        (round_dir / "validator-alpha-report.md").touch()
        (round_dir / "validator-beta-report.md").touch()

        result = reports.list_validator_reports(round_dir)

        names = [f.name for f in result]
        assert names == sorted(names)
