"""Tests for error handling in report I/O operations.

NO MOCKS - real config, real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path
import os

import pytest

from edison.core.qa.evidence import reports
from edison.core.qa.evidence.exceptions import EvidenceError


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_write_bundle_report_fails_on_readonly_dir(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should raise EvidenceError when cannot write to directory."""
        # Make directory read-only
        os.chmod(round_dir, 0o444)

        try:
            data = {"status": "test"}

            with pytest.raises(EvidenceError) as exc_info:
                reports.write_bundle_report(
                    round_dir, data, repo_root=isolated_project_env
                )

            assert "Failed to write bundle summary" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            os.chmod(round_dir, 0o755)

    def test_write_implementation_report_fails_on_readonly_dir(
        self, isolated_project_env: Path, round_dir: Path
    ):
        """Should raise EvidenceError when cannot write implementation report."""
        os.chmod(round_dir, 0o444)

        try:
            data = {"files": ["test.py"]}

            with pytest.raises(EvidenceError) as exc_info:
                reports.write_implementation_report(
                    round_dir, data, repo_root=isolated_project_env
                )

            assert "Failed to write implementation report" in str(exc_info.value)
        finally:
            os.chmod(round_dir, 0o755)

    def test_write_validator_report_fails_on_readonly_dir(self, round_dir: Path):
        """Should raise EvidenceError when cannot write validator report."""
        os.chmod(round_dir, 0o444)

        try:
            data = {"score": 100}

            with pytest.raises(EvidenceError) as exc_info:
                reports.write_validator_report(round_dir, "test", data)

            assert "Failed to write validator report" in str(exc_info.value)
        finally:
            os.chmod(round_dir, 0o755)
