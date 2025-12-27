from __future__ import annotations

from pathlib import Path

import yaml

from edison.core.rules import RulesRegistry


def test_company_layer_rules_registry_is_applied(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    company_dir = root / "company-layer"
    (company_dir / "config").mkdir(parents=True)

    company_rules = company_dir / "rules" / "registry.yml"
    company_rules.parent.mkdir(parents=True, exist_ok=True)
    with open(company_rules, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "RULE.COMPANY.STANDARD",
                        "title": "Company standard rule",
                        "category": "process",
                        "blocking": False,
                        "applies_to": ["agent"],
                        "guidance": "Company rule guidance.",
                    }
                ],
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

    registry = RulesRegistry(project_root=root)
    composed = registry.compose(packs=[])
    assert "RULE.COMPANY.STANDARD" in composed["rules"]

