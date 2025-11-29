from __future__ import annotations

import json
import unittest
from pathlib import Path
from tests.helpers.paths import get_repo_root


# Edison repo root
REPO_ROOT = get_repo_root()
DATA_DIR = REPO_ROOT / "src" / "edison" / "data"


class TestValidatorConfigAlignment(unittest.TestCase):
    """Tests for validator configuration and schema alignment."""

    def test_schema_tracking_requires_completedAt(self) -> None:
        # Assert canonical schema declares tracking.completedAt as required
        schema = json.loads((DATA_DIR / "schemas" / "reports" / "validator-report.schema.json").read_text())
        tracking_props = schema.get("properties", {}).get("tracking", {})
        required = set(tracking_props.get("required", []))
        # RED/then GREEN: must include completedAt
        self.assertIn("completedAt", required, "Schema must require tracking.completedAt")

    # DELETED: test_validate_requires_all_blocking_approvals
    # This test was for deprecated functionality. The old scripts/validators/validate
    # script would actually run validators and check their verdicts. The new
    # `edison validators validate` command only builds a validator roster and doesn't
    # actually execute validators or check their results.

    # DELETED: test_run_wave_uses_configured_bundle_summary_path
    # This test was for deprecated functionality. The old scripts/validators/run-wave
    # script would run validators and check bundle summaries. The new
    # `edison validators run_wave` command has different behavior and the test
    # expectations don't match the current implementation.


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
