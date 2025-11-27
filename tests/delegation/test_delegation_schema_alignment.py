from __future__ import annotations

import json
import subprocess
from pathlib import Path
import unittest
import pytest
from edison.core.utils.subprocess import run_with_timeout

REPO_ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.skip(reason="Deprecated: Schema location changed to edison/data/schemas, old .edison/core paths removed")
class DelegationSchemaAlignmentTests(unittest.TestCase):
    def test_single_canonical_schema_file(self) -> None:
        # There must be exactly one delegation-config.schema.json and it must be the canonical path
        matches = list(REPO_ROOT.rglob("delegation-config.schema.json"))
        self.assertGreaterEqual(len(matches), 1, "No delegation-config.schema.json found")
        canonical = REPO_ROOT / ".edison" / "core" / "schemas" / "config" / "delegation-config.schema.json"
        # Expect exactly one and it is canonical
        self.assertEqual(
            [p.relative_to(REPO_ROOT).as_posix() for p in matches],
            [canonical.relative_to(REPO_ROOT).as_posix()],
            f"Expected only canonical schema at {canonical}, found: {[p.as_posix() for p in matches]}",
        )

    def test_schema_enum_excludes_none(self) -> None:
        # Load canonical schema and assert that no enum contains 'none'
        schema_path = REPO_ROOT / ".edison" / "core" / "schemas" / "config" / "delegation-config.schema.json"
        schema = json.loads(schema_path.read_text())

        def walk(o: object) -> list[list[str]]:
            enums: list[list[str]] = []
            if isinstance(o, dict):
                if "enum" in o and isinstance(o["enum"], list):
                    enums.append(o["enum"]) 
                for v in o.values():
                    enums.extend(walk(v))
            elif isinstance(o, list):
                for v in o:
                    enums.extend(walk(v))
            return enums

        all_enums = walk(schema)
        for e in all_enums:
            self.assertNotIn("none", e, f"Schema enum still allows 'none': {e}")

    def test_config_points_to_canonical_schema_and_validates(self) -> None:
        # config.json must point to canonical schema path
        cfg_path = REPO_ROOT / ".edison" / "core" / "delegation" / "config.json"
        cfg = json.loads(cfg_path.read_text())
        self.assertIn("$schema", cfg, "config.json missing $schema")
        self.assertTrue(
            str(cfg["$schema"]).endswith("/schemas/config/delegation-config.schema.json")
            or str(cfg["$schema"]).endswith("../schemas/config/delegation-config.schema.json"),
            f"$schema should point to canonical schema, got: {cfg.get('$schema')}",
        )

        # And it should validate via the CLI helper (exit code 0)
        validate_cli = REPO_ROOT / ".edison" / "core" / "scripts" / "delegation" / "validate"
        res = run_with_timeout([str(validate_cli), "config", "--path", str(cfg_path)], cwd=REPO_ROOT, text=True, capture_output=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()