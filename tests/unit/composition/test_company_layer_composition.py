from __future__ import annotations

from pathlib import Path

from edison.core.composition.registries.agent_prompts import AgentPromptRegistry


def test_company_layer_agent_new_entity_is_discovered_and_composed(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    company_dir = root / "company-layer"
    (company_dir / "config").mkdir(parents=True)
    (company_dir / "agents").mkdir(parents=True, exist_ok=True)
    (company_dir / "agents" / "company-agent.md").write_text(
        "Company agent content.\n",
        encoding="utf-8",
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

    registry = AgentPromptRegistry(project_root=root)
    content = registry.compose("company-agent", packs=[])
    assert content is not None
    assert "Company agent content." in content
