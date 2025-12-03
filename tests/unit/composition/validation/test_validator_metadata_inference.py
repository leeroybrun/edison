"""Tests for validator metadata inference utilities.

These tests verify that metadata can be correctly inferred from validator
markdown files, with proper fallback to sensible defaults when files are
missing or parsing fails.

NO MOCKS - real files, real behavior.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import infer_validator_metadata


class TestMetadataInference:
    """Test metadata inference for validators defined only by ID."""

    def test_infer_validator_metadata_returns_defaults_when_file_missing(
        self, tmp_path: Path
    ) -> None:
        """When no validator file exists, return sensible defaults."""
        repo_root = tmp_path / "repo"
        project_dir = tmp_path / "project"
        packs_dir = tmp_path / "packs"
        repo_root.mkdir()
        project_dir.mkdir()
        packs_dir.mkdir()

        result = infer_validator_metadata(
            validator_id="missing-validator",
            project_root=repo_root,
            project_dir=project_dir,
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
            project_root=repo_root,
            project_dir=project_dir,
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
            project_root=repo_root,
            project_dir=project_dir,
            active_packs=["react"],
        )

        assert result["name"] == "Jsx Validator"
        assert result["model"] == "codex"
        assert result["triggers"] == ["*"]

    def test_infer_validator_metadata_skips_core_edison_principles_header(
        self, tmp_path: Path
    ) -> None:
        """Skip 'Core Edison Principles' header and use the next one."""
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
            project_root=repo_root,
            project_dir=project_dir,
            active_packs=[],
        )

        assert result["name"] == "Actual Validator Name"

    def test_infer_validator_metadata_handles_multiple_triggers(
        self, tmp_path: Path
    ) -> None:
        """Parse multiple triggers from backtick-quoted patterns."""
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
            project_root=repo_root,
            project_dir=project_dir,
            active_packs=[],
        )

        assert result["triggers"] == ["*.ts", "*.tsx", "*.js", "*.jsx"]

    def test_infer_validator_metadata_handles_read_errors_gracefully(
        self, tmp_path: Path
    ) -> None:
        """Return defaults if file exists but cannot be read."""
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
                project_root=repo_root,
                project_dir=project_dir,
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
            project_root=repo_root,
            project_dir=project_dir,
            active_packs=[],
        )

        # Should use project version
        assert result["name"] == "Project Override Validator"
        assert result["model"] == "gemini"
