from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
import pytest
from edison.core.utils.subprocess import run_with_timeout


REPO_ROOT = Path(__file__).resolve().parents[4]
VALIDATE = REPO_ROOT / ".edison" / "core" / "scripts" / "delegation" / "validate"


@pytest.mark.skip(reason="Deprecated: Old delegation CLI removed, functionality moved to edison.core.delegation")
class DelegationNoMatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work = Path(tempfile.mkdtemp(prefix="delegation-nomatch-"))
        self.addCleanup(lambda: shutil.rmtree(self.work, ignore_errors=True))

    def run_cli(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return run_with_timeout([str(VALIDATE), *argv], cwd=REPO_ROOT, text=True, capture_output=True)

    def write_config(self, data: dict) -> Path:
        p = self.work / "config.json"
        p.write_text(json.dumps(data, indent=2))
        return p

    def minimal_base_config(self) -> dict:
        return {
            "filePatternRules": {},
            "taskTypeRules": {},
            "subAgentDefaults": {
                "api-builder": {"defaultModel": "codex"},
                "feature-implementer": {"defaultModel": "gemini"},
            },
            "orchestratorGuidance": {"alwaysDelegateToSubAgent": True, "neverImplementDirectly": True},
            "zenMcpIntegration": {"enabled": True, "availableModels": {"codex": {}, "gemini": {}}},
        }

    def test_no_match_returns_error(self) -> None:
        """Verify no-match scenario returns error exit code"""
        cfg = self.minimal_base_config()
        path = self.write_config(cfg)
        res = self.run_cli(
            "decide", "--json", "--path", str(path), "--task-type", "unknown-type"
        )
        # Expect failure (non-zero) when no rules match
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        # Should emit JSON with NO_MATCH code
        out = json.loads(res.stdout or "{}")
        self.assertEqual(out.get("code"), "NO_MATCH")
        self.assertIn("No delegation rule matches", out.get("error", ""))
        # Echo back context for debugging
        self.assertEqual(out.get("taskType"), "unknown-type")
        self.assertIsInstance(out.get("files"), list)

    def test_no_match_provides_suggestions(self) -> None:
        """Verify error message guides users to fix"""
        cfg = self.minimal_base_config()
        path = self.write_config(cfg)
        res = self.run_cli("decide", "--path", str(path), "--task-type", "none-here")
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        # Helpful guidance in stderr
        err = (res.stderr or "") + (res.stdout or "")
        self.assertIn("No delegation rule matches", err)
        self.assertIn("Add a default rule", err)
        self.assertIn("--model", err)  # suggests override path

    def test_successful_match_still_returns_zero(self) -> None:
        """Verify matching rules still return exit 0"""
        cfg = self.minimal_base_config()
        cfg["taskTypeRules"] = {
            "documentation": {
                "preferredModel": "gemini",
                "subAgentType": "feature-implementer",
                "delegation": "required",
                "preferredZenRole": "project-feature-implementer",
            }
        }
        path = self.write_config(cfg)
        res = self.run_cli("decide", "--json", "--path", str(path), "--task-type", "documentation")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        out = json.loads(res.stdout or "{}")
        sel = out.get("selected") or {}
        self.assertEqual(sel.get("model"), "gemini")
        # role comes from preferredZenRole when provided
        self.assertIn(sel.get("subAgentType"), {"feature-implementer"})
        self.assertEqual(sel.get("role"), "project-feature-implementer")
        self.assertNotIn("error", out)

    def test_error_json_format(self) -> None:
        """Verify error JSON has correct structure"""
        cfg = self.minimal_base_config()
        path = self.write_config(cfg)
        res = self.run_cli(
            "decide", "--json", "--path", str(path), "--task-type", "unknown", "--file", "unmatched.ts"
        )
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        out = json.loads(res.stdout or "{}")
        self.assertIn("error", out)
        self.assertEqual(out.get("code"), "NO_MATCH")
        self.assertEqual(out.get("taskType"), "unknown")
        self.assertEqual(out.get("files"), ["unmatched.ts"])  # echoes input files


if __name__ == "__main__":
    unittest.main()