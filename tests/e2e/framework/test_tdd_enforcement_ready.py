import os
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

# Unit tests targeting TDD enforcement logic in `.agents/scripts/tasks/ready` and
# `scripts/tdd-verification.sh`. These start RED by asserting missing/weak
# behaviors that we will implement (GREEN) in subsequent patches.


class FakeCompleted:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


class TddEnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        # Create an isolated tmp directory inside repo for evidence files
        self.tmp = Path(".agents/scripts/tests/tmp-tdd").resolve()
        if self.tmp.exists():
            import shutil
            shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        # Do not aggressively remove to keep artifacts for debugging failures
        pass

    def test_71_exit_codes_enforced_when_generating_evidence(self):
        """RED: tasks/ready should fail when test command exits non‑zero.

        We expect a helper `generate_evidence_files` in tasks/ready that:
        - runs commands
        - writes files
        - raises SystemExit if any command returns non‑zero
        """
        import types, runpy
        mod_dict = runpy.run_path(str(Path(".agents/scripts/tasks/ready").resolve()))
        ready = types.SimpleNamespace(**mod_dict)

        latest = self.tmp / "round-1"
        latest.mkdir(parents=True, exist_ok=True)

        cmds = {
            "command-type-check.txt": "echo typecheck && exit 0",
            "command-lint.txt": "echo lint && exit 0",
            "command-test.txt": "echo tests && exit 1",  # force failure
            "command-build.txt": "echo build && exit 0",
        }

        # Intentionally fails BEFORE implementation adds enforcement
        with self.assertRaises(SystemExit):
            ready.generate_evidence_files(latest, cmds, run_cmd=lambda c, cwd: FakeCompleted(1) if "tests" in c else FakeCompleted(0))

    def test_74_timestamp_validation_blocks_fabricated_evidence(self):
        """RED: fabricated evidence without trusted runner markers must be rejected.

        We expect a `validate_evidence_integrity(latest_dir, started_at_iso)` that:
        - checks mtime >= started_at and within a freshness window
        - checks file content contains a runner marker and exit code line
        """
        import types, runpy
        mod_dict = runpy.run_path(str(Path(".agents/scripts/tasks/ready").resolve()))
        ready = types.SimpleNamespace(**mod_dict)

        latest = self.tmp / "round-1"
        latest.mkdir(parents=True, exist_ok=True)
        for name in [
            "command-type-check.txt",
            "command-lint.txt",
            "command-test.txt",
            "command-build.txt",
        ]:
            (latest / name).write_text("Mock evidence\nExit code: 0\n", encoding="utf-8")

        started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600))

        with self.assertRaises(SystemExit):
            ready.validate_evidence_integrity(latest, started_at)

    def test_72_75_git_red_before_green_required(self):
        """RED: require RED→GREEN ordering and tests before implementation.

        We expect `ensure_tdd_red_green(started_at, base_branch)` to inspect git log
        and raise when there is no RED commit before GREEN or when implementation
        precedes tests. We'll simulate via a fake provider.
        """
        import types, runpy
        mod_dict = runpy.run_path(str(Path(".agents/scripts/tasks/ready").resolve()))
        ready = types.SimpleNamespace(**mod_dict)

        # Fake git commits: GREEN only → should fail
        commits = [
            {"message": "feat: implement feature [GREEN]", "files": ["src/feature.ts"]},
        ]

        def fake_commits_since(_started_at: str, _base: str):
            return commits

        with self.assertRaises(SystemExit):
            ready.ensure_tdd_red_green(
                started_at_iso="2025-01-01T00:00:00Z",
                base_branch="main",
                commit_provider=fake_commits_since,
            )

    def test_73_verification_script_thresholds(self):
        """RED: tdd-verification.sh must require 90% overall and 100% new code.

        This test is textual to avoid heavy environment coupling. It asserts
        presence of explicit anchors that the script must expose.
        """
        script = Path("scripts/tdd-verification.sh").read_text(encoding="utf-8")
        self.assertIn("TDD_ENFORCEMENT: REQUIRED_COVERAGE=90", script)
        self.assertIn("TDD_ENFORCEMENT: NEW_CODE_COVERAGE=100", script)


if __name__ == "__main__":
    unittest.main()
