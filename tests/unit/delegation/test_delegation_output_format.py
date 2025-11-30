"""Tests for Delegation OUTPUT_FORMAT correctness and schema alignment.

These tests ensure the delegation OUTPUT_FORMAT doc reflects the implemented
structure and that the schema aligns with the implementation tooling.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest
import pytest
from tests.helpers.paths import get_repo_root


REPO_ROOT = get_repo_root()


@pytest.mark.skip(reason="Deprecated: Old delegation OUTPUT_FORMAT.md removed, schema location changed")
class TestDelegationOutputFormat(unittest.TestCase):
    def setUp(self) -> None:
        self.doc_path = REPO_ROOT / ".edison" / "core" / "delegation" / "OUTPUT_FORMAT.md"
        self.schema_path = REPO_ROOT / ".edison" / "core" / "schemas" / "reports" / "delegation-report.schema.json"
        self.impl_report_path = REPO_ROOT / ".agents" / "implementation" / "OUTPUT_FORMAT.md"

    def test_doc_header_and_schema_reference(self) -> None:
        text = self.doc_path.read_text()
        # Must be about Delegation, not Implementation
        self.assertRegex(text.splitlines()[0].strip(), r"^#\s+Delegation Report Output Format")
        # Must reference the correct schema path
        self.assertIn(".edison/core/schemas/reports/delegation-report.schema.json", text)

    def test_schema_fields_match_implementation_delegations(self) -> None:
        """Schema must align with `edison implementation report --add-delegation` format.

        Implementation expects delegations[] entries with keys:
        - filePattern (required), model (required), role (required)
        Optional: rationale, continuationId, outcome
        """
        schema = json.loads(self.schema_path.read_text())
        deleg = schema.get("properties", {}).get("delegations", {})
        items = deleg.get("items", {})
        required = set(items.get("required", []))
        self.assertIn("filePattern", required, "delegation item must require filePattern (not path)")
        self.assertIn("model", required)
        self.assertIn("role", required)
        props = set((items.get("properties") or {}).keys())
        for key in ["rationale", "continuationId", "outcome"]:
            self.assertIn(key, props, f"optional key missing in schema: {key}")


if __name__ == "__main__":
    unittest.main()
