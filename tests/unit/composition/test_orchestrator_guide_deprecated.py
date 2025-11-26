"""Tests for ORCHESTRATOR_GUIDE.md deprecation (T-011).

STRICT TDD: These tests ensure ORCHESTRATOR_GUIDE.md is NO LONGER GENERATED.
Constitution system (constitutions/ORCHESTRATORS.md) replaces it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition import CompositionEngine


class TestOrchestratorGuideDeprecation:
    """Verify ORCHESTRATOR_GUIDE.md is NO LONGER generated after T-011."""

    def _write_defaults(self, core_dir: Path) -> None:
        """Write minimal defaults.yaml for tests."""
        try:
            import yaml  # type: ignore
        except Exception as err:
            pytest.skip(f"PyYAML not available: {err}")

        defaults = {
            "validation": {
                "roster": {
                    "global": [
                        {"name": "global-codex", "model": "codex", "blocking": False},
                    ],
                    "critical": [],
                    "specialized": [],
                }
            },
            "delegation": {
                "filePatterns": {},
                "taskTypes": {},
            },
        }
        (core_dir / "defaults.yaml").write_text(
            yaml.safe_dump(defaults), encoding="utf-8"
        )

    def _write_core_guidelines(self, core_dir: Path) -> None:
        """Write minimal core guidelines."""
        guidelines_dir = core_dir / "guidelines"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        (guidelines_dir / "SESSION_WORKFLOW.md").write_text(
            "# Session Workflow", encoding="utf-8"
        )
        (guidelines_dir / "DELEGATION.md").write_text(
            "# Delegation", encoding="utf-8"
        )
        (guidelines_dir / "TDD.md").write_text("# TDD", encoding="utf-8")

    def test_compose_orchestrator_does_NOT_create_orchestrator_guide_md(
        self, tmp_path: Path
    ) -> None:
        """ORCHESTRATOR_GUIDE.md must NOT be generated after deprecation.

        This test FAILS initially (RED), then passes when we update
        compose_orchestrator_manifest() to NOT write ORCHESTRATOR_GUIDE.md.
        """
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        core_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": []},
            "validation": {
                "roster": {
                    "global": [
                        {"name": "global-codex", "model": "codex", "blocking": False},
                    ],
                    "critical": [],
                    "specialized": [],
                }
            },
            "delegation": {
                "filePatterns": {},
                "taskTypes": {},
            },
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".edison" / "_generated"

        result = engine.compose_orchestrator_manifest(output_dir)

        # CRITICAL: ORCHESTRATOR_GUIDE.md must NOT be in result
        assert "markdown" not in result, (
            "compose_orchestrator_manifest must NOT return 'markdown' key "
            "after deprecation. Constitution system replaces ORCHESTRATOR_GUIDE.md."
        )

        # CRITICAL: File must NOT exist on disk
        orchestrator_guide = output_dir / "ORCHESTRATOR_GUIDE.md"
        assert not orchestrator_guide.exists(), (
            f"ORCHESTRATOR_GUIDE.md must NOT be generated at {orchestrator_guide}. "
            "Use constitutions/ORCHESTRATORS.md instead."
        )

    def test_compose_orchestrator_still_creates_json_manifest(
        self, tmp_path: Path
    ) -> None:
        """JSON manifest (orchestrator-manifest.json) must STILL be generated.

        Only ORCHESTRATOR_GUIDE.md is deprecated. JSON manifest remains.
        """
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        core_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": []},
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".edison" / "_generated"

        result = engine.compose_orchestrator_manifest(output_dir)

        # JSON manifest MUST still be generated
        assert "json" in result, "orchestrator-manifest.json must still be generated"
        assert result["json"].exists(), "JSON manifest file must exist"

        # Verify JSON content is valid
        import json
        json_data = json.loads(result["json"].read_text(encoding="utf-8"))
        assert json_data["version"] == "2.0.0"
        assert "validators" in json_data
        assert "agents" in json_data

    def test_compose_all_does_NOT_generate_orchestrator_guide_md(
        self, tmp_path: Path
    ) -> None:
        """Integration test: `edison compose all` must NOT generate ORCHESTRATOR_GUIDE.md.

        This validates compose CLI integration.
        """
        repo_root = tmp_path
        core_dir = repo_root / ".edison" / "core"
        core_dir.mkdir(parents=True, exist_ok=True)

        self._write_defaults(core_dir)
        self._write_core_guidelines(core_dir)

        config = {
            "project": {"name": "test-project"},
            "packs": {"active": []},
        }

        engine = CompositionEngine(config, repo_root=repo_root)
        output_dir = repo_root / ".edison" / "_generated"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Simulate `edison compose all --orchestrator`
        result = engine.compose_orchestrator_manifest(output_dir)

        # ORCHESTRATOR_GUIDE.md must NOT exist
        orchestrator_guide = output_dir / "ORCHESTRATOR_GUIDE.md"
        assert not orchestrator_guide.exists(), (
            "compose all --orchestrator must NOT generate ORCHESTRATOR_GUIDE.md"
        )

        # JSON manifest MUST exist
        assert result["json"].exists()
