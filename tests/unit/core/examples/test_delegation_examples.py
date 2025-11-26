from __future__ import annotations

from pathlib import Path


def test_delegation_example_files_exist():
    repo_root = Path(__file__).resolve().parents[4]
    examples_dir = repo_root / "src/edison/data/examples/delegation"

    expected_files = {
        "feature-implementation.example.md",
        "api-endpoint.example.md",
        "component-creation.example.md",
        "database-schema.example.md",
        "test-writing.example.md",
    }

    assert examples_dir.is_dir(), f"Examples directory missing: {examples_dir}"

    existing = {p.name for p in examples_dir.glob("*.md")}
    missing = expected_files - existing
    assert not missing, f"Missing delegation example files: {sorted(missing)}"
