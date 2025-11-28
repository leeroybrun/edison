from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.paths import get_repo_root


REPO_ROOT = get_repo_root()


class RulesRegistryAnchorsTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure consistent environment; most scripts resolve paths relative to repo root.
        self.env = os.environ.copy()

    def run_cli(self, *parts: str) -> subprocess.CompletedProcess[str]:
        return run_with_timeout(
            list(parts),
            cwd=REPO_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_all_rule_ids_resolve_and_extract(self) -> None:
        # Prefer the canonical Edison core registry location inside .edison/.
        registry_path = REPO_ROOT / ".edison" / "core" / "rules" / "registry.json"
        self.assertTrue(registry_path.exists(), f"Missing registry: {registry_path}")
        data = json.loads(registry_path.read_text())
        rules = data.get("rules", [])
        self.assertGreater(len(rules), 0, "No rules found in registry")

        failures: list[str] = []
        for item in rules:
            rid = item["id"]
            source_path = REPO_ROOT / item["sourcePath"]
            if not source_path.exists():
                failures.append(f"{rid}: source file not found: {source_path}")
                continue

            # Use the canonical CLI to verify anchors and extraction.
            res = self.run_cli(
                str(REPO_ROOT / ".edison" / "core" / "scripts" / "rules"),
                "show",
                rid,
                "--format",
                "json",
            )
            if res.returncode != 0:
                failures.append(f"{rid}: extraction failed (rc={res.returncode})\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}")
                continue

            try:
                payload = json.loads(res.stdout or "{}")
            except Exception as e:
                failures.append(f"{rid}: invalid JSON from rules CLI: {e}\nSTDOUT:\n{res.stdout}")
                continue

            # Basic payload assertions
            if payload.get("id") != rid:
                failures.append(f"{rid}: payload id mismatch: {payload.get('id')}")
            start_anchor = payload.get("startAnchor")
            end_anchor = payload.get("endAnchor")
            if not start_anchor or not end_anchor:
                failures.append(f"{rid}: missing start/end anchors in payload")
            content = payload.get("content") or ""
            if not isinstance(content, str) or content.strip() == "":
                failures.append(f"{rid}: extracted content is empty")

        if failures:
            self.fail("Rules registry anchor check failed:\n- " + "\n- ".join(failures))


if __name__ == "__main__":
    unittest.main()