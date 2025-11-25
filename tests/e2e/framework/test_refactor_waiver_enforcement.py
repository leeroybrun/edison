import runpy
import types
import unittest
from pathlib import Path


class RefactorWaiverTests(unittest.TestCase):
    def setUp(self) -> None:  # noqa: D401
        # load lib module dictionary directly from path to avoid import caching side-effects
        mod_dict = runpy.run_path(str((Path('.edison/core/lib/tddlib.py')).resolve()))
        self.tddlib = types.SimpleNamespace(**mod_dict)

    def test_valid_red_green_refactor_sequence(self):
        commits = [
            {"message": "[RED] initial failing test"},
            {"message": "[GREEN] make test pass"},
            {"message": "[REFACTOR] cleanup"},
        ]

        def provider(_started_at: str, _base: str):
            return commits

        ok = self.tddlib._validate_refactor_cycle(
            task_id="T-TEST-OK",
            commit_provider=provider,
        )
        self.assertTrue(ok)

    def test_invalid_red_refactor_sequence_fails(self):
        commits = [
            {"message": "[RED] failing test"},
            {"message": "[REFACTOR] attempted cleanup without green"},
        ]

        def provider(_started_at: str, _base: str):
            return commits

        ok = self.tddlib._validate_refactor_cycle(
            task_id="T-TEST-FAIL",
            commit_provider=provider,
        )
        self.assertFalse(ok)

    def test_no_commits_is_valid(self):
        def provider(_started_at: str, _base: str):
            return []

        ok = self.tddlib._validate_refactor_cycle(
            task_id="T-TEST-EMPTY",
            commit_provider=provider,
        )
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()

