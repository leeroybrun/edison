from __future__ import annotations

from pathlib import Path

import yaml


PACKS = {
    "typescript": {
        "files": [
            "pack.yml",
            "defaults.yaml",
            "pack-dependencies.yaml",
            "validators/codex-context.md",
            "validators/claude-context.md",
            "validators/gemini-context.md",
            "guidelines/strict-mode.md",
            "guidelines/type-safety.md",
            "guidelines/advanced-types.md",
            "examples/strict-config.json",
            "examples/type-patterns.ts",
        ],
    },
    "react": {
        "files": [
            "pack.yml",
            "defaults.yaml",
            "pack-dependencies.yaml",
            "validators/codex-context.md",
            "validators/claude-context.md",
            "validators/gemini-context.md",
            "guidelines/hooks-patterns.md",
            "guidelines/component-design.md",
            "guidelines/server-client-components.md",
            "guidelines/accessibility.md",
            "examples/server-component.tsx",
            "examples/client-component.tsx",
            "examples/custom-hook.ts",
        ],
    },
    "nextjs": {
        "files": [
            "pack.yml",
            "defaults.yaml",
            "pack-dependencies.yaml",
            "validators/codex-context.md",
            "validators/claude-context.md",
            "validators/gemini-context.md",
            "guidelines/app-router.md",
            "guidelines/route-handlers.md",
            "guidelines/server-actions.md",
            "guidelines/metadata.md",
            "guidelines/caching.md",
            "examples/route-handler.ts",
            "examples/server-action.ts",
            "examples/dynamic-metadata.ts",
        ],
    },
    "fastify": {
        "files": [
            "pack.yml",
            "defaults.yaml",
            "pack-dependencies.yaml",
            "validators/codex-context.md",
            "validators/claude-context.md",
            "validators/gemini-context.md",
            "guidelines/schema-validation.md",
            "guidelines/error-handling.md",
            "guidelines/auth.md",
            "examples/route.ts",
            "examples/error-handler.ts",
            "examples/auth-plugin.ts",
        ],
    },
    "prisma": {
        "files": [
            "pack.yml",
            "defaults.yaml",
            "pack-dependencies.yaml",
            "validators/codex-context.md",
            "validators/claude-context.md",
            "validators/gemini-context.md",
            "guidelines/schema-design.md",
            "guidelines/migrations.md",
            "guidelines/query-optimization.md",
            "guidelines/relationships.md",
            "examples/schema.prisma",
            "examples/migration.sql",
            "examples/query-patterns.ts",
        ],
    },
    "uistyles": {
        "files": [
            "pack.yml",
            "defaults.yaml",
            "pack-dependencies.yaml",
            "validators/codex-context.md",
            "validators/claude-context.md",
            "validators/gemini-context.md",
            "guidelines/v4-syntax.md",
            "guidelines/design-tokens.md",
            "guidelines/responsive.md",
            "examples/globals.css",
            "examples/uistyles.config.ts",
            "examples/component-patterns.tsx",
        ],
    },
    "vitest": {
        "files": [
            "pack.yml",
            "defaults.yaml",
            "pack-dependencies.yaml",
            "validators/codex-context.md",
            "validators/claude-context.md",
            "validators/gemini-context.md",
            "guidelines/tdd-workflow.md",
            "guidelines/test-quality.md",
            "guidelines/api-testing.md",
            "guidelines/component-testing.md",
            "examples/api-route.test.ts",
            "examples/component.test.tsx",
        ],
    },
}


def test_pack_scaffolds_exist():
    root = Path.cwd() / ".edison" / "packs"
    assert root.exists(), "Missing .edison/packs directory"
    for name, spec in PACKS.items():
        pdir = root / name
        assert pdir.exists(), f"Pack missing: {name}"
        for rel in spec["files"]:
            f = pdir / rel
            assert f.exists(), f"Missing file for {name}: {rel}"


def test_pack_validators_per_role_exist():
    """Each pack must provide codex/claude/gemini validator contexts."""
    root = Path.cwd() / ".edison" / "packs"
    for name in PACKS.keys():
        pdir = root / name / "validators"
        assert pdir.exists(), f"Missing validators directory for {name}"
        for role in ("codex", "claude", "gemini"):
            path = pdir / f"{role}-context.md"
            assert path.exists(), f"Missing {role}-context.md for pack {name}"


def test_pack_triggers_use_file_patterns_object():
    """Pack YAML must declare triggers.filePatterns (no legacy list form)."""
    root = Path.cwd() / ".edison" / "packs"
    for name in PACKS.keys():
        yml = root / name / "pack.yml"
        assert yml.exists(), f"Missing pack.yml for {name}"
        data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        triggers = data.get("triggers")
        assert isinstance(triggers, dict), f"triggers must be an object for {name}"
        patterns = triggers.get("filePatterns")
        assert isinstance(patterns, list) and patterns, f"triggers.filePatterns must be a non-empty list for {name}"
