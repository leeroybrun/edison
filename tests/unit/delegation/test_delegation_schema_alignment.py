from __future__ import annotations

import unittest
from edison.data import get_data_path
from edison.core.utils.io import read_yaml


class TestDelegationSchemaAlignment(unittest.TestCase):
    def test_single_canonical_schema_file(self) -> None:
        core = get_data_path("schemas")
        matches = list(core.rglob("delegation-config.schema.yaml"))
        self.assertEqual(len(matches), 1, f"Expected exactly 1 canonical schema, found: {matches}")
        canonical = get_data_path("schemas", "config/delegation-config.schema.yaml")
        self.assertEqual(matches[0].resolve(), canonical.resolve())

    def test_schema_enum_excludes_none(self) -> None:
        # Load canonical schema and assert that no enum contains 'none'
        schema_path = get_data_path("schemas", "config/delegation-config.schema.yaml")
        schema = read_yaml(schema_path, default={}, raise_on_error=True)

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


if __name__ == "__main__":
    unittest.main()
