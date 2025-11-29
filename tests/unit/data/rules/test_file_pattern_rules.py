from pathlib import Path

import pytest

from edison.core.rules import FilePatternRegistry


ROOT = Path(__file__).resolve().parents[4]


def _get_get_ids(rules):
    return {rule.get("id") for rule in rules}


def _get_get_stems(rules):
    return {Path(rule.get("_path", "")).stem for rule in rules if rule.get("_path")}


def test_core_file_pattern_rules_are_generic_only() -> None:
    """Core file pattern rules must exclude tech-specific stacks."""
    registry = FilePatternRegistry(repo_root=ROOT)
    core_rules = registry.load_core_rules()

    stems = _get_stems(core_rules)
    assert stems == {"api", "testing"}

    ids = _get_ids(core_rules)
    banned = {
        "FILE_PATTERN.REACT_COMPONENT",
        "FILE_PATTERN.NEXTJS_APP_ROUTER",
        "FILE_PATTERN.TAILWIND_CONFIG",
        "FILE_PATTERN.DATABASE",
    }
    assert ids.isdisjoint(banned), "Core must not ship tech-specific file pattern rules"


@pytest.mark.parametrize(
    "packs,expected_ids",
    [
        (
            ["react", "nextjs", "prisma", "tailwind"],
            {
                "FILE_PATTERN.REACT_COMPONENT",
                "FILE_PATTERN.NEXTJS_APP_ROUTER",
                "FILE_PATTERN.TAILWIND_CONFIG",
                "FILE_PATTERN.DATABASE",
            },
        )
    ],
)
def test_pack_file_patterns_load_when_active(packs, expected_ids) -> None:
    """Pack registries must contribute tech-specific file pattern rules when active."""
    registry = FilePatternRegistry(repo_root=ROOT)

    composed = registry.compose(active_packs=packs)
    composed_ids = _get_ids(composed)
    for rid in expected_ids:
        assert rid in composed_ids, f"Missing pack rule {rid} for packs {packs}"

    origins = {rule["id"]: rule.get("_origin") for rule in composed if rule.get("id") in expected_ids}
    for rid in expected_ids:
        assert origins.get(rid, "").startswith("pack:"), f"{rid} should be marked as pack-origin"

    # Baseline: without packs, tech-specific rules should not appear
    core_only_ids = _get_ids(registry.compose(active_packs=[]))
    assert core_only_ids.isdisjoint(expected_ids)
