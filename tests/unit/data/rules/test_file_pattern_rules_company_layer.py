from __future__ import annotations

from pathlib import Path

import yaml

from edison.core.composition.registries.file_patterns import FilePatternRegistry


def test_company_layer_pack_file_patterns_load_when_active(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    company_dir = root / "company-layer"
    (company_dir / "config").mkdir(parents=True)

    # Company provides a pack with file pattern rules.
    pack_rules = company_dir / "packs" / "company-pack" / "rules" / "file_patterns"
    pack_rules.mkdir(parents=True, exist_ok=True)
    with open(pack_rules / "company.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {
                "id": "FILE_PATTERN.COMPANY_SPECIAL",
                "name": "Company special",
                "patterns": ["**/*.company"],
                "validators": ["company"],
            },
            f,
            sort_keys=False,
        )

    proj_cfg = root / ".edison" / "config"
    proj_cfg.mkdir(parents=True, exist_ok=True)
    (proj_cfg / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company_dir.as_posix()}\n"
        "      before: user\n",
        encoding="utf-8",
    )

    registry = FilePatternRegistry(repo_root=root)
    composed = registry.compose(active_packs=["company-pack"])
    ids = {r.get("id") for r in composed if isinstance(r, dict)}
    assert "FILE_PATTERN.COMPANY_SPECIAL" in ids

