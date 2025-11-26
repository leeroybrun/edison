from __future__ import annotations

"""Tests for validator metadata inference utilities.

These tests verify that metadata can be correctly inferred from validator
markdown files, with proper fallback to sensible defaults when files are
missing or parsing fails.
"""

from pathlib import Path

import pytest


class TestMetadataInference:
    """Test metadata inference for validators defined only by ID."""

    def test_infer_validator_metadata_returns_defaults_when_file_missing(
        self, tmp_path: Path
    ) -> None:
        """When no validator file exists, return sensible defaults."""
        from edison.core.composition.validator_metadata import infer_validator_metadata

        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"
        repo_root.mkdir()
        project_dir.mkdir()
        packs_dir.mkdir()

        result = infer_validator_metadata(
            validator_id="missing-validator",
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=[],
        )

        assert result["id"] == "missing-validator"
        assert result["name"] == "Missing Validator"
        assert result["model"] == "codex"
        assert result["triggers"] == ["*"]
        assert result["alwaysRun"] is False
        assert result["blocksOnFail"] is False

    def test_infer_validator_metadata_parses_name_from_header(
        self, tmp_path: Path
    ) -> None:
        """Extract validator name from first markdown header."""
        from edison.core.composition.validator_metadata import infer_validator_metadata

        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"
        validators_dir = project_dir / "validators" / "specialized"
        validators_dir.mkdir(parents=True)

        # Create validator file with header
        validator_file = validators_dir / "python-imports.md"
        validator_file.write_text(
            """# Python Import Validator

**Model**: codex
**Triggers**: `*.py`
**Blocks on Fail**: ✅ YES
""",
            encoding="utf-8",
        )

        result = infer_validator_metadata(
            validator_id="python-imports",
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=[],
        )

        assert result["name"] == "Python Import Validator"
        assert result["model"] == "codex"
        assert result["triggers"] == ["*.py"]
        assert result["blocksOnFail"] is True

    def test_infer_validator_metadata_searches_multiple_paths(
        self, tmp_path: Path
    ) -> None:
        """Search paths in priority order: project, repo, packs."""
        from edison.core.composition.validator_metadata import infer_validator_metadata

        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"

        # Create validator in pack directory
        pack_validators = packs_dir / "react" / "validators"
        pack_validators.mkdir(parents=True)
        (pack_validators / "jsx-validator.md").write_text(
            """# JSX Component Validator

**Model**: gemini
**Triggers**: `*.jsx`, `*.tsx`
""",
            encoding="utf-8",
        )

        result = infer_validator_metadata(
            validator_id="jsx-validator",
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=["react"],
        )

        assert result["name"] == "JSX Component Validator"
        assert result["model"] == "gemini"
        assert result["triggers"] == ["*.jsx", "*.tsx"]

    def test_infer_validator_metadata_skips_core_edison_principles_header(
        self, tmp_path: Path
    ) -> None:
        """Skip 'Core Edison Principles' header and use the next one."""
        from edison.core.composition.validator_metadata import infer_validator_metadata

        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"
        validators_dir = project_dir / "validators" / "specialized"
        validators_dir.mkdir(parents=True)

        validator_file = validators_dir / "test-validator.md"
        validator_file.write_text(
            """# Core Edison Principles

# Actual Validator Name

**Model**: codex
""",
            encoding="utf-8",
        )

        result = infer_validator_metadata(
            validator_id="test-validator",
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=[],
        )

        assert result["name"] == "Actual Validator Name"

    def test_infer_validator_metadata_handles_multiple_triggers(
        self, tmp_path: Path
    ) -> None:
        """Parse multiple triggers from backtick-quoted patterns."""
        from edison.core.composition.validator_metadata import infer_validator_metadata

        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"
        validators_dir = project_dir / "validators" / "specialized"
        validators_dir.mkdir(parents=True)

        validator_file = validators_dir / "multi-trigger.md"
        validator_file.write_text(
            """# Multi Trigger Validator

**Triggers**: `*.ts`, `*.tsx`, `*.js`, `*.jsx`
""",
            encoding="utf-8",
        )

        result = infer_validator_metadata(
            validator_id="multi-trigger",
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=[],
        )

        assert result["triggers"] == ["*.ts", "*.tsx", "*.js", "*.jsx"]

    def test_infer_validator_metadata_handles_read_errors_gracefully(
        self, tmp_path: Path
    ) -> None:
        """Return defaults if file exists but cannot be read."""
        from edison.core.composition.validator_metadata import infer_validator_metadata

        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"
        validators_dir = project_dir / "validators" / "specialized"
        validators_dir.mkdir(parents=True)

        # Create file, then make it unreadable (on Unix)
        validator_file = validators_dir / "unreadable.md"
        validator_file.write_text("# Test", encoding="utf-8")
        validator_file.chmod(0o000)

        try:
            result = infer_validator_metadata(
                validator_id="unreadable",
                repo_root=repo_root,
                project_dir=project_dir,
                packs_dir=packs_dir,
                active_packs=[],
            )

            # Should return defaults
            assert result["id"] == "unreadable"
            assert result["model"] == "codex"
        finally:
            # Restore permissions for cleanup
            validator_file.chmod(0o644)

    def test_infer_validator_metadata_prioritizes_project_over_core(
        self, tmp_path: Path
    ) -> None:
        """Project validator definitions override core definitions."""
        from edison.core.composition.validator_metadata import infer_validator_metadata

        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"

        # Create core validator
        core_validators = repo_root / ".edison" / "core" / "validators" / "specialized"
        core_validators.mkdir(parents=True)
        (core_validators / "shared-validator.md").write_text(
            """# Core Shared Validator

**Model**: codex
""",
            encoding="utf-8",
        )

        # Create project override
        project_validators = project_dir / "validators" / "specialized"
        project_validators.mkdir(parents=True)
        (project_validators / "shared-validator.md").write_text(
            """# Project Override Validator

**Model**: gemini
""",
            encoding="utf-8",
        )

        result = infer_validator_metadata(
            validator_id="shared-validator",
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=[],
        )

        # Should use project version
        assert result["name"] == "Project Override Validator"
        assert result["model"] == "gemini"


class TestNormalizeValidatorEntries:
    """Test normalization of validator roster entries."""

    def test_normalize_validator_entries_preserves_dict_entries(
        self, tmp_path: Path
    ) -> None:
        """Dict entries with 'id' are passed through unchanged."""
        from edison.core.composition.validator_metadata import normalize_validator_entries

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
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=[],
        )

        assert len(result) == 2
        assert result[0] == raw_entries[0]
        assert result[1] == raw_entries[1]

    def test_normalize_validator_entries_expands_string_ids_from_fallback_map(
        self, tmp_path: Path
    ) -> None:
        """String IDs are expanded using fallback map if available."""
        from edison.core.composition.validator_metadata import normalize_validator_entries

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
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=[],
        )

        assert len(result) == 2
        assert result[0] == fallback_map["validator-1"]
        assert result[1] == fallback_map["validator-2"]

    def test_normalize_validator_entries_infers_metadata_for_unknown_ids(
        self, tmp_path: Path
    ) -> None:
        """String IDs not in fallback map trigger metadata inference."""
        from edison.core.composition.validator_metadata import normalize_validator_entries

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
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
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
        from edison.core.composition.validator_metadata import normalize_validator_entries

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
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=[],
        )

        # Only 2 valid entries
        assert len(result) == 2
        assert result[0]["id"] == "validator-1"
        assert result[1]["id"] == "validator-2"
