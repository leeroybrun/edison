import unittest

# sys.path is already configured by tests/conftest.py
# Import directly from helpers module file to avoid circular import issues
from helpers.tdd_helpers import _validate_refactor_cycle


class TestRefactorWaiver(unittest.TestCase):
    def setUp(self) -> None:  # noqa: D401
        # Direct import from test helpers
        self.tddlib = type('TddLib', (), {'_validate_refactor_cycle': _validate_refactor_cycle})()

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

