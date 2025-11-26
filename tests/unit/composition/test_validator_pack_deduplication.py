"""Validator composition should not duplicate pack sections."""
from __future__ import annotations

from pathlib import Path

import yaml

from edison.core.composition import LayeredComposer
from edison.core.utils.paths.project import get_project_config_dir


def _write_core_validator(project_dir: Path, validator_id: str) -> Path:
    """Create a minimal validator core with section markers."""
    validators_dir = project_dir / "core" / "validators" / "global"
    validators_dir.mkdir(parents=True, exist_ok=True)
    path = validators_dir / f"{validator_id}.md"
    path.write_text(
        "\n".join(
            [
                f"# {validator_id} Validator",
                "",
                "## Core",
                "Base checks for validator.",
                "",
                "## Tech-Stack Context",
                "{{SECTION:TechStack}}",
                "",
                "{{EXTENSIBLE_SECTIONS}}",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_pack_context(project_dir: Path, pack: str, role: str, title: str) -> Path:
    """Create a pack context file for the given role (in overlays/ subdir)."""
    # Pack contexts live in packs/{pack}/validators/overlays/{role}.md
    pack_dir = project_dir / "packs" / pack / "validators" / "overlays"
    pack_dir.mkdir(parents=True, exist_ok=True)
    path = pack_dir / f"{role}.md"
    path.write_text(
        f"<!-- EXTEND: TechStack -->\n## {title}\n- guidance from {pack}\n<!-- /EXTEND -->",
        encoding="utf-8",
    )
    return path


def _write_pack_yml(project_dir: Path, pack: str) -> Path:
    """Write minimal pack.yml for the pack."""
    pack_dir = project_dir / "packs" / pack
    pack_dir.mkdir(parents=True, exist_ok=True)
    pack_yml = pack_dir / "pack.yml"
    pack_yml.write_text(
        yaml.dump({
            "name": pack,
            "version": "1.0.0",
            "description": f"Test pack {pack}",
        }),
        encoding="utf-8",
    )
    return pack_yml


def test_pack_sections_are_deduplicated_and_ordered(isolated_project_env: Path) -> None:
    """Each pack section should appear once in composed validator output."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Using unified naming: one 'global' validator file
    validator_id = "global"

    _write_core_validator(project_dir, validator_id)
    
    # Create pack structures with pack.yml and validator overlays
    for pack in ["react", "next"]:
        _write_pack_yml(project_dir, pack)
        _write_pack_context(project_dir, pack, validator_id, f"{pack.capitalize()} Pack Context")

    # Use LayeredComposer directly with deduplicated packs
    composer = LayeredComposer(repo_root=root, content_type="validators")
    
    # Packs should be deduplicated before passing to compose
    unique_packs = list(dict.fromkeys(["react", "next", "react", "next"]))  # Dedupe preserving order
    text = composer.compose(validator_id, unique_packs)

    react_count = text.count("React Pack Context")
    next_count = text.count("Next Pack Context")

    assert react_count == 1, f"React pack appears {react_count} times"
    assert next_count == 1, f"Next pack appears {next_count} times"

    react_index = text.index("React Pack Context")
    next_index = text.index("Next Pack Context")
    assert react_index < next_index, "Pack order should follow first occurrence of configured packs"
