"""Tests for normalization of validator roster entries.

NO MOCKS - real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import normalize_validator_entries


class TestNormalizeValidatorEntries:
    """Test normalization of validator roster entries."""

    def test_normalize_validator_entries_preserves_dict_entries(
        self, tmp_path: Path
    ) -> None:
        """Dict entries with 'id' are passed through unchanged."""
        repo_root = tmp_path
        project_dir = tmp_path
        packs_dir = tmp_path

        raw_entries = [
            {"id": "validator-1", "name": "Validator One", "model": "codex"},
            {"id": "validator-2", "name": "Validator Two", "model": "gemini"},
        ]

        result = normalize_validator_entries(
            raw_entries,
            fallback_map={},
            project_root=repo_root,
            project_dir=project_dir,
            active_packs=[],
        )

        assert len(result) == 2
        assert result[0] == raw_entries[0]
        assert result[1] == raw_entries[1]

    def test_normalize_validator_entries_expands_string_ids_from_fallback_map(
        self, tmp_path: Path
    ) -> None:
        """String IDs are expanded using fallback map if available."""
        repo_root = tmp_path
        project_dir = tmp_path
        packs_dir = tmp_path

        fallback_map = {
            "validator-1": {"id": "validator-1", "name": "Validator One", "model": "codex"},
            "validator-2": {"id": "validator-2", "name": "Validator Two", "model": "gemini"},
        }

        raw_entries = ["validator-1", "validator-2"]

        result = normalize_validator_entries(
            raw_entries,
            fallback_map=fallback_map,
            project_root=repo_root,
            project_dir=project_dir,
            active_packs=[],
        )

        assert len(result) == 2
        assert result[0] == fallback_map["validator-1"]
        assert result[1] == fallback_map["validator-2"]

    def test_normalize_validator_entries_infers_metadata_for_unknown_ids(
        self, tmp_path: Path
    ) -> None:
        """String IDs not in fallback map trigger metadata inference."""
        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"
        repo_root.mkdir()
        project_dir.mkdir()
        packs_dir.mkdir()

        validators_dir = project_dir / "validators" / "specialized"
        validators_dir.mkdir(parents=True)
        (validators_dir / "new-validator.md").write_text(
            """# New Validator

**Model**: gemini
""",
            encoding="utf-8",
        )

        raw_entries = ["new-validator"]

        result = normalize_validator_entries(
            raw_entries,
            fallback_map={},
            project_root=repo_root,
            project_dir=project_dir,
            active_packs=[],
        )

        assert len(result) == 1
        assert result[0]["id"] == "new-validator"
        assert result[0]["name"] == "New Validator"
        assert result[0]["model"] == "gemini"

    def test_normalize_validator_entries_filters_empty_strings(
        self, tmp_path: Path
    ) -> None:
        """Empty strings are filtered out."""
        repo_root = tmp_path
        project_dir = tmp_path
        packs_dir = tmp_path

        raw_entries = ["validator-1", "", "validator-2", None]
        fallback_map = {
            "validator-1": {"id": "validator-1", "model": "codex"},
            "validator-2": {"id": "validator-2", "model": "gemini"},
        }

        result = normalize_validator_entries(
            raw_entries,
            fallback_map=fallback_map,
            project_root=repo_root,
            project_dir=project_dir,
            active_packs=[],
        )

        # Only 2 valid entries
        assert len(result) == 2
        assert result[0]["id"] == "validator-1"
        assert result[1]["id"] == "validator-2"
