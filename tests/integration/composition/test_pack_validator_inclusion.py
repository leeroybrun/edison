from __future__ import annotations

from pathlib import Path

import sys
import pytest

# Ensure Edison core lib is importable
REPO_ROOT = Path(__file__).resolve().parents[5]
core_path = REPO_ROOT / ".edison" / "core"
from edison.core.composition import CompositionEngine 
class TestPackValidatorInclusion:
    def test_composed_validators_include_pack_content(self):
        """Composed validators should include real pack context, not missing comments."""
        # Use the real repository configuration and packs
        engine = CompositionEngine()
        results = engine.compose_validators()

        assert "codex-global" in results
        codex_result = results["codex-global"]

        content = codex_result.text

        # Pack content from at least one real pack should be present
        # (React pack is expected to be active in this project config)
        assert "React Validation Context" in content

        # "Missing pack context" comments must not appear once packs are wired correctly
        assert "Missing pack context" not in content

    def test_renamed_validators_discovered_by_composition(self):
        """Pack validators in the real repo should use the new naming."""
        repo_root = Path.cwd()

        packs_dir = repo_root / ".edison" / "packs"
        assert packs_dir.exists(), f"Packs directory does not exist: {packs_dir}"

        found_legacy = []

        for pack_dir in packs_dir.iterdir():
            if not pack_dir.is_dir():
                continue

            validators_dir = pack_dir / "validators"
            if not validators_dir.exists():
                continue

            codex_context = validators_dir / "codex-context.md"
            legacy = validators_dir / "codex-global-context.md"

            # When codex-context exists, legacy name must not exist
            if codex_context.exists():
                assert not legacy.exists(), f"Legacy file still exists: {legacy}"
            else:
                # Track packs that still need migration for clearer failures
                if legacy.exists():
                    found_legacy.append(legacy)

        if found_legacy:
            pytest.fail(
                "Found packs with legacy codex-global-context.md and no codex-context.md: "
                + ", ".join(str(p) for p in found_legacy)
            )

    def test_multi_provider_pack_contexts_are_included(self):
        """All global validators (codex/claude/gemini) must include pack contexts."""
        engine = CompositionEngine()
        results = engine.compose_validators(validator="all")

        for vid in ("codex-global", "claude-global", "gemini-global"):
            assert vid in results, f"{vid} missing from composed validators"
            text = results[vid].text
            # React pack context should appear for each provider
            assert "React Validation Context" in text, f"React context missing from {vid}"
