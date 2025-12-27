from __future__ import annotations

from pathlib import Path

from edison.core.composition.packs import discover_packs


def _write_minimal_pack(pack_dir: Path, *, name: str) -> None:
    """Write the minimum valid pack structure for discover_packs()."""
    (pack_dir / "validators" / "overlays").mkdir(parents=True, exist_ok=True)
    (pack_dir / "validators" / "overlays" / "global.md").write_text(
        "# Global validator overlay\n", encoding="utf-8"
    )
    (pack_dir / "pack.yml").write_text(
        "\n".join(
            [
                f"name: {name}",
                "version: 0.0.1",
                "description: test pack",
                "triggers:",
                "  filePatterns:",
                "    - \"**/*\"",
                "validators: []",
                "examples: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_discover_packs_includes_user_packs(tmp_path: Path) -> None:
    """discover_packs() includes packs from ~/.edison/packs in addition to project packs."""
    # User pack root is forced to tmp_path/.edison-user by tests/conftest.py
    user_pack_dir = tmp_path / ".edison-user" / "packs" / "user-pack"
    _write_minimal_pack(user_pack_dir, name="user-pack")

    packs = {p.name for p in discover_packs(root=tmp_path)}
    assert "user-pack" in packs


def test_user_pack_shadows_bundled_pack(tmp_path: Path) -> None:
    """When a pack exists in bundled + user roots, user pack takes precedence."""
    # Pick a known bundled pack name so discover_packs sees both.
    user_pack_dir = tmp_path / ".edison-user" / "packs" / "python"
    _write_minimal_pack(user_pack_dir, name="python")

    packs = discover_packs(root=tmp_path)
    python_pack = [p for p in packs if p.name == "python"][0]
    assert python_pack.path.resolve() == user_pack_dir.resolve()
