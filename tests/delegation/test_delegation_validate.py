from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout

REPO_ROOT = Path(__file__).resolve().parents[4]
VALIDATE = REPO_ROOT / ".edison" / "core" / "scripts" / "delegation" / "validate"


class DelegationValidateCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.work = Path(tempfile.mkdtemp(prefix="delegation-validate-"))
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

    def test_policy_conflict_detection(self) -> None:
        cfg = self.minimal_base_config()
        cfg["taskTypeRules"] = {
            "documentation": {
                "preferredModel": "gemini",
                "subAgentType": "feature-implementer",
                "delegation": "none",  # violates neverImplementDirectly
            }
        }
        path = self.write_config(cfg)
        res = self.run_cli("config", "--path", str(path))
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("neverImplementDirectly", res.stdout + res.stderr)

    def test_full_stack_requires_multi_model_when_partial(self) -> None:
        cfg = self.minimal_base_config()
        cfg["taskTypeRules"] = {
            "full-stack-feature": {
                "preferredModel": "gemini",  # single model
                "subAgentType": "feature-implementer",
                "delegation": "partial",  # requires multi-model
            }
        }
        path = self.write_config(cfg)
        res = self.run_cli("config", "--path", str(path))
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("multi-model", res.stdout + res.stderr)

    def test_schema_required_fields(self) -> None:
        # Missing orchestratorGuidance
        bad = {
            "filePatternRules": {},
            "taskTypeRules": {},
            "subAgentDefaults": {},
            "zenMcpIntegration": {"enabled": True, "availableModels": {"codex": {}, "gemini": {}}},
        }
        path = self.write_config(bad)
        res = self.run_cli("config", "--path", str(path))
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("schema", (res.stdout + res.stderr).lower())

    def test_decide_tie_breaker_prefers_file_pattern(self) -> None:
        cfg = self.minimal_base_config()
        cfg["filePatternRules"] = {
            "**/route.ts": {
                "preferredModel": "codex",
                "subAgentType": "api-builder",
                "delegation": "required",
            }
        }
        cfg["taskTypeRules"] = {
            "full-stack-feature": {
                "preferredModel": "gemini",
                "subAgentType": "feature-implementer",
                "delegation": "partial",
                "preferredModels": ["gemini", "codex"],
            }
        }
        cfg["orchestratorGuidance"]["tieBreakers"] = {
            "order": ["filePatternRules", "taskTypeRules", "subAgentDefaults"],
            "modelPriority": ["codex", "gemini", "claude"],
            "subAgentPriority": ["api-builder", "feature-implementer"],
        }
        path = self.write_config(cfg)
        # ask the CLI to decide for a full-stack task that touches an API route
        res = self.run_cli(
            "decide",
            "--path",
            str(path),
            "--task-type",
            "full-stack-feature",
            "--file",
            "src/app/api/leads/route.ts",
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        try:
            out = json.loads(res.stdout or "{}")
        except Exception:
            self.fail(f"Invalid JSON output: {res.stdout}\n{res.stderr}")
        self.assertEqual(out.get("selected", {}).get("subAgentType"), "api-builder")
        self.assertEqual(out.get("selected", {}).get("model"), "codex")

    def test_valid_config_passes(self) -> None:
        cfg = self.minimal_base_config()
        cfg["taskTypeRules"] = {
            "documentation": {
                "preferredModel": "gemini",
                "subAgentType": "feature-implementer",
                "delegation": "required",
            },
            "architecture-design": {
                "preferredModel": "gemini",
                "subAgentType": "feature-implementer",
                "delegation": "required",
            },
            "full-stack-feature": {
                "preferredModel": "multi",
                "preferredModels": ["gemini", "codex"],
                "subAgentType": "feature-implementer",
                "delegation": "partial",
            },
        }
        cfg["orchestratorGuidance"]["tieBreakers"] = {
            "order": ["filePatternRules", "taskTypeRules", "subAgentDefaults"],
            "modelPriority": ["codex", "gemini", "claude"],
            "subAgentPriority": ["api-builder", "feature-implementer"],
        }
        path = self.write_config(cfg)
        res = self.run_cli("config", "--path", str(path))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()