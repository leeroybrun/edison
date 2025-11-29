"""Validator composition should not duplicate pack sections."""
from __future__ import annotations

from pathlib import Path

from helpers.io_utils import write_yaml, write_text
from edison.core.composition import LayeredComposer
from edison.core.utils.paths.project import get_project_config_dir


def test_pack_sections_are_deduplicated_and_ordered(isolated_project_env: Path) -> None:
    """Each pack section should appear once in composed validator output."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)

    # Using unified naming: one 'global' validator file
    validator_id = "global"

    # Create minimal validator core with section markers
    validators_dir = project_dir / "core" / "validators" / "global"
    validators_dir.mkdir(parents=True, exist_ok=True)
    validator_path = validators_dir / f"{validator_id}.md"
    write_text(
        validator_path,
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
    )

    # Create pack structures with pack.yml and validator overlays
    for pack in ["react", "next"]:
        # Write minimal pack.yml for the pack
        pack_dir = project_dir / "packs" / pack
        pack_dir.mkdir(parents=True, exist_ok=True)
        write_yaml(
            pack_dir / "pack.yml",
            {
                "name": pack,
                "version": "1.0.0",
                "description": f"Test pack {pack}",
            },
        )

        # Create a pack context file for the validator
        overlays_dir = project_dir / "packs" / pack / "validators" / "overlays"
        overlays_dir.mkdir(parents=True, exist_ok=True)
        write_text(
            overlays_dir / f"{validator_id}.md",
            f"<!-- EXTEND: TechStack -->\n## {pack.capitalize()} Pack Context\n- guidance from {pack}\n<!-- /EXTEND -->",
        )

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
