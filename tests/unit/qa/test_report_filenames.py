"""Tests for configuration-based report filename resolution.

NO MOCKS - real config, real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.qa.evidence import reports


class TestGetReportFilenames:
    """Test configuration-based filename resolution."""

    def test_default_filenames_when_no_config(self, isolated_project_env: Path):
        """Should return default filenames when config doesn't specify custom ones."""
        filenames = reports.get_report_filenames(isolated_project_env)

        # Defaults from defaults.yaml
        assert filenames["bundle"] == "bundle-approved.json"
        assert filenames["implementation"] == "implementation-report.json"

    def test_custom_filenames_from_config(self, isolated_qa_config: Path):
        """Should return custom filenames from QA config."""
        filenames = reports.get_report_filenames(isolated_qa_config)

        assert filenames["bundle"] == "custom-bundle.json"
        assert filenames["implementation"] == "custom-impl.json"
