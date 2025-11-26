"""Validator composition should not duplicate pack sections."""
from __future__ import annotations

from pathlib import Path

import yaml

from edison.core.composition import CompositionEngine


def _write_core_validator(root: Path, validator_id: str) -> Path:
    """Create a minimal validator core with PACK_CONTEXT placeholder."""
    validators_dir = root / ".edison" / "core" / "validators" / "global"
    validators_dir.mkdir(parents=True, exist_ok=True)
    path = validators_dir / f"{validator_id}-core.md"
    path.write_text(
        "\n".join(
            [
                f"# {validator_id} Validator",
                "",
                "## Core",
                "Base checks for validator.",
                "",
                "## Packs",
                "{{PACK_CONTEXT}}",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_pack_context(root: Path, pack: str, role: str, title: str) -> Path:
    """Create a pack context file for the given role."""
    pack_dir = root / ".edison" / "packs" / pack / "validators"
    pack_dir.mkdir(parents=True, exist_ok=True)
    path = pack_dir / f"{role}-context.md"
    path.write_text(f"## {title}\n- guidance from {pack}", encoding="utf-8")
    return path


def _write_config_with_packs(root: Path, packs: list[str]) -> Path:
    """Write config.yml enabling the provided packs."""
    config_path = root / ".edison" / "config" / "config.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "packs": {"active": packs},
        "validation": {"roster": {"global": [{"id": "codex-global"}]}},
    }
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    return config_path


def test_pack_sections_are_deduplicated_and_ordered(isolated_project_env: Path) -> None:
    """Each pack section should appear once in composed validator output."""
    root = isolated_project_env
    validator_id = "codex"

    _write_core_validator(root, validator_id)
    _write_pack_context(root, "react", validator_id, "React Pack Context")
    _write_pack_context(root, "next", validator_id, "Next Pack Context")
    _write_config_with_packs(root, ["react", "next", "react", "next"])

    engine = CompositionEngine(repo_root=root)
    results = engine.compose_validators(validator=validator_id, enforce_dry=False)
    text = results["codex-global"].text

    react_count = text.count("React Pack Context")
    next_count = text.count("Next Pack Context")

    assert react_count == 1, f"React pack appears {react_count} times"
    assert next_count == 1, f"Next pack appears {next_count} times"
    assert text.count("# Tech-Stack Context (Packs)") == 1, "Pack section heading should be single"

    react_index = text.index("React Pack Context")
    next_index = text.index("Next Pack Context")
    assert react_index < next_index, "Pack order should follow first occurrence of configured packs"
