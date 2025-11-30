from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
import unittest

import yaml
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.paths import get_repo_root, get_core_root


REPO_ROOT = get_repo_root()
SCRIPTS_ROOT = get_core_root() / "scripts"


def _copy_minimal_repo(dst_root: Path) -> None:
    """Copy minimal Edison structures needed for rules tests into dst_root.

    This keeps tests real (no mocks) while avoiding mutation of the main repo.
    Guidelines and other files are now in bundled data, so we copy from there.
    """
    from edison.data import get_data_path

    # Registry JSON - check both bundled data and legacy locations
    src_reg = get_data_path("rules", "registry.json")
    if not src_reg.exists():
        # Fallback to legacy location
        src_reg = REPO_ROOT / ".edison" / "core" / "rules" / "registry.json"

    if src_reg.exists():
        dst_reg = dst_root / ".edison" / "core" / "rules" / "registry.json"
        dst_reg.parent.mkdir(parents=True, exist_ok=True)
        dst_reg.write_bytes(src_reg.read_bytes())

    # Guideline files referenced by the registry - now in bundled data
    src_guidelines_dir = get_data_path("guidelines")
    dst_guidelines_dir = dst_root / ".edison" / "core" / "guidelines"
    if src_guidelines_dir.exists():
        # Shallow copy of all guideline files – cheap and keeps behavior realistic.
        dst_guidelines_dir.mkdir(parents=True, exist_ok=True)
        for path in src_guidelines_dir.glob("**/*.md"):
            # Preserve subdirectory structure
            rel_path = path.relative_to(src_guidelines_dir)
            target = dst_guidelines_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())

    # Additional rule sources referenced by the registry
    # START.SESSION.md is now START_NEW_SESSION.md in bundled data
    extra_sources = [
        ("start", "START_NEW_SESSION.md", ".edison/core/guides/START.SESSION.md"),
        ("validators", "OUTPUT_FORMAT.md", ".edison/core/validators/OUTPUT_FORMAT.md"),
    ]
    for subpkg, filename, legacy_path in extra_sources:
        src = get_data_path(subpkg, filename)
        if not src.exists():
            # Fallback to legacy location
            src = REPO_ROOT / legacy_path
        if src.exists():
            # Write to expected test location (legacy path structure for test compatibility)
            dst = dst_root / legacy_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())


class TestRulesRegistryMigration(unittest.TestCase):
    def setUp(self) -> None:
        self.env = os.environ.copy()

    def _run_python(self, script: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
        return run_with_timeout(
            ["python3", str(script)],
            cwd=cwd,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_migrate_registry_paths_fixes_agents_prefixes_and_verifies_paths(self) -> None:
        """migrate-registry-paths must fix legacy .agents prefixes and verify paths."""
        with tempfile.TemporaryDirectory(prefix="rules-migration-") as tmp:
            tmp_root = Path(tmp)
            _copy_minimal_repo(tmp_root)

            reg_path = tmp_root / ".edison" / "core" / "rules" / "registry.json"
            data = json.loads(reg_path.read_text())

            # Simulate legacy broken paths by rewriting guidelines prefix back to .agents/.
            for rule in data.get("rules", []):
                sp = rule.get("sourcePath", "")
                # Check for both legacy and bundled data paths
                if sp.startswith(".edison/core/guidelines/") or sp.startswith("guidelines/"):
                    # Replace with legacy .agents/ path to test migration
                    base_name = sp.split("/")[-1]
                    rule["sourcePath"] = f".agents/guidelines/{base_name}"
            reg_path.write_text(json.dumps(data, indent=2))

            script = SCRIPTS_ROOT / "rules_migrate_registry_paths.py"
            proc = self._run_python(script, cwd=tmp_root)
            self.assertEqual(
                proc.returncode,
                0,
                msg=f"migrate-registry-paths failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
            )

            updated = json.loads(reg_path.read_text())
            for rule in updated.get("rules", []):
                source_path = rule.get("sourcePath", "")
                self.assertFalse(
                    source_path.startswith(".agents/"),
                    f"Path not migrated away from .agents/: {source_path}",
                )
                file_part = source_path.split("#", 1)[0]
                full = (tmp_root / file_part).resolve()
                self.assertTrue(
                    full.exists(),
                    f"Missing rule source for {rule.get('id')}: {full}",
                )


class TestRulesRegistryYamlConversion(unittest.TestCase):
    def setUp(self) -> None:
        self.env = os.environ.copy()

    def _run_python(self, script: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
        return run_with_timeout(
            ["python3", str(script)],
            cwd=cwd,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_json_to_yaml_migration_creates_yaml_with_all_rules(self) -> None:
        """json-to-yaml-migration must emit registry.yml with all rules and metadata."""
        with tempfile.TemporaryDirectory(prefix="rules-yaml-") as tmp:
            tmp_root = Path(tmp)
            _copy_minimal_repo(tmp_root)

            json_path = tmp_root / ".edison" / "core" / "rules" / "registry.json"
            orig = json.loads(json_path.read_text())

            script = SCRIPTS_ROOT / "rules_json_to_yaml_migration.py"
            proc = self._run_python(script, cwd=tmp_root)
            self.assertEqual(
                proc.returncode,
                0,
                msg=f"json-to-yaml-migration failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
            )

            yaml_path = tmp_root / ".edison" / "core" / "rules" / "registry.yml"
            self.assertTrue(yaml_path.exists(), "registry.yml was not created")

            data = yaml.safe_load(yaml_path.read_text())
            self.assertIsInstance(data, dict)
            self.assertIn("version", data)
            self.assertEqual(
                data.get("version"),
                "2.0.0",
                "YAML registry version should be bumped to 2.0.0",
            )

            rules = data.get("rules", [])
            self.assertEqual(
                len(rules),
                len(orig.get("rules", [])),
                "YAML registry must carry all rules from JSON registry",
            )

            for rule in rules:
                for key in ("id", "title", "category", "blocking", "sourcePath", "guidance"):
                    self.assertIn(key, rule, f"Missing key '{key}' in YAML rule: {rule}")

            # Spot-check that known anchors are present in YAML sourcePath entries,
            # ready for anchor verification.
            idx = {r["id"]: r for r in rules}
            self.assertIn("RULE.DELEGATION.PRIORITY_CHAIN", idx)
            self.assertTrue(
                idx["RULE.DELEGATION.PRIORITY_CHAIN"]["sourcePath"].endswith("#priority-chain"),
                "Delegation priority chain rule should carry #priority-chain anchor",
            )
            self.assertIn("RULE.VALIDATION.FIRST", idx)
            self.assertTrue(
                idx["RULE.VALIDATION.FIRST"]["sourcePath"].endswith("#validation-first"),
                "Validation-first rule should carry #validation-first anchor",
            )
            self.assertIn("RULE.CONTEXT.BUDGET_MINIMIZE", idx)
            self.assertTrue(
                idx["RULE.CONTEXT.BUDGET_MINIMIZE"]["sourcePath"].endswith("#context-budget"),
                "Context budget rule should carry #context-budget anchor",
            )


class TestRulesAnchorsAndContextCli(unittest.TestCase):
    def setUp(self) -> None:
        self.env = os.environ.copy()

    def _run_python(self, script: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return run_with_timeout(
            ["python3", str(script), *extra],
            cwd=REPO_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def _run_rules_cli(self, *parts: str) -> subprocess.CompletedProcess[str]:
        cli = SCRIPTS_ROOT / "rules"
        return run_with_timeout(
            [str(cli), *parts],
            cwd=REPO_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_verify_anchors_script_succeeds_after_yaml_migration(self) -> None:
        """verify-anchors must exit successfully once YAML registry exists."""
        # Ensure YAML registry is present for the real repo.
        yaml_migration = SCRIPTS_ROOT / "rules_json_to_yaml_migration.py"
        proc_migrate = self._run_python(yaml_migration)
        # The migration script may be a no-op if YAML already exists, but it must succeed.
        self.assertEqual(
            proc_migrate.returncode,
            0,
            msg=f"json-to-yaml-migration failed in real repo\nSTDOUT:\n{proc_migrate.stdout}\nSTDERR:\n{proc_migrate.stderr}",
        )

        verify_script = SCRIPTS_ROOT / "rules_verify_anchors.py"
        proc_verify = self._run_python(verify_script)
        self.assertEqual(
            proc_verify.returncode,
            0,
            msg=f"verify-anchors reported problems\nSTDOUT:\n{proc_verify.stdout}\nSTDERR:\n{proc_verify.stderr}",
        )

    def test_show_for_context_guidance_delegation_lists_delegation_rules(self) -> None:
        """rules show-for-context must surface delegation rules for guidance:delegation."""
        # Ensure YAML registry exists for CLI to consume.
        yaml_migration = SCRIPTS_ROOT / "rules_json_to_yaml_migration.py"
        proc_migrate = self._run_python(yaml_migration)
        self.assertEqual(
            proc_migrate.returncode,
            0,
            msg=f"json-to-yaml-migration failed in real repo\nSTDOUT:\n{proc_migrate.stdout}\nSTDERR:\n{proc_migrate.stderr}",
        )

        proc = self._run_rules_cli("show-for-context", "guidance", "delegation")
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"rules show-for-context failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        stdout = proc.stdout
        self.assertIn("Applicable Rules for guidance:delegation", stdout)
        # At least one delegation rule should be listed.
        self.assertIn("RULE.DELEGATION.PRIORITY_CHAIN", stdout)


if __name__ == "__main__":
    unittest.main()