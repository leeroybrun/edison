from __future__ import annotations
from helpers.io_utils import write_yaml

from pathlib import Path

from edison.core.config import ConfigManager
from edison.core.composition.registries import constitutions as constitution

def _make_config_manager(repo_root: Path, packs: list[str] | None = None, constitution_cfg: dict | None = None) -> ConfigManager:
    """Create a ConfigManager rooted at repo_root with optional overlays."""
    if packs is not None:
        write_yaml(
            repo_root / ".edison" / "config" / "packs.yml",
            {"packs": {"active": packs}},
        )

    if constitution_cfg is not None:
        write_yaml(
            repo_root / ".edison" / "core" / "config" / "constitution.yaml",
            constitution_cfg,
        )

    return ConfigManager(repo_root)

def test_get_rules_for_role_filters_by_applies_to() -> None:
    """Rules should be filtered by applies_to with no mocks."""
    agent_rules = constitution.get_rules_for_role("agent")

    assert agent_rules, "Expected at least one agent rule"
    assert all("agent" in r.get("applies_to", []) for r in agent_rules)

def test_load_constitution_layer_reads_each_layer(tmp_path: Path) -> None:
    core_dir = tmp_path / "core"
    pack_dir = tmp_path / "pack"
    project_dir = tmp_path / "project"

    (core_dir / "constitutions").mkdir(parents=True, exist_ok=True)
    (core_dir / "constitutions" / "orchestrator-base.md").write_text("core-base", encoding="utf-8")

    (pack_dir / "constitutions").mkdir(parents=True, exist_ok=True)
    (pack_dir / "constitutions" / "orchestrator-additions.md").write_text("pack-add", encoding="utf-8")

    (project_dir / "constitutions").mkdir(parents=True, exist_ok=True)
    (project_dir / "constitutions" / "orchestrator-overrides.md").write_text("project-override", encoding="utf-8")

    assert constitution.load_constitution_layer(core_dir, "orchestrator", "core") == "core-base"
    assert constitution.load_constitution_layer(pack_dir, "orchestrator", "pack") == "pack-add"
    assert constitution.load_constitution_layer(project_dir, "orchestrator", "project") == "project-override"
    assert constitution.load_constitution_layer(project_dir, "agents", "project") == ""

def test_compose_constitution_merges_core_pack_project(tmp_path: Path) -> None:
    repo_root = tmp_path
    core_const_dir = repo_root / ".edison" / "core" / "constitutions"
    pack_const_dir = repo_root / ".edison" / "packs" / "demo" / "constitutions"
    project_const_dir = repo_root / ".edison" / "constitutions"

    core_const_dir.mkdir(parents=True, exist_ok=True)
    pack_const_dir.mkdir(parents=True, exist_ok=True)
    project_const_dir.mkdir(parents=True, exist_ok=True)

    (core_const_dir / "orchestrator-base.md").write_text("CORE {{source_layers}}", encoding="utf-8")
    (pack_const_dir / "orchestrator-additions.md").write_text("PACK demo", encoding="utf-8")
    (project_const_dir / "orchestrator-overrides.md").write_text("PROJECT", encoding="utf-8")

    cfg_mgr = _make_config_manager(repo_root, packs=["demo"])

    composed = constitution.compose_constitution("orchestrator", cfg_mgr)

    assert "CORE" in composed
    assert "PACK demo" in composed
    assert "PROJECT" in composed
    assert composed.index("CORE") < composed.index("PACK demo") < composed.index("PROJECT")
    assert "core" in composed.lower() and "project" in composed.lower()

def test_render_constitution_template_replaces_placeholders(tmp_path: Path) -> None:
    repo_root = tmp_path
    constitution_cfg = {
        "mandatoryReads": {
            "agents": [
                {"path": "docs/A.md", "purpose": "Alpha"},
                {"path": "docs/B.md", "purpose": "Beta"},
            ]
        }
    }
    cfg_mgr = _make_config_manager(repo_root, constitution_cfg=constitution_cfg)

    template = (
        "{{#each mandatoryReads.agents}}\n"
        "- {{this.path}} :: {{this.purpose}}\n"
        "{{/each}}\n"
        "{{#each rules.agent}}\n"
        "* {{this.id}} - {{this.name}}\n"
        "{{/each}}\n"
        "Src: {{source_layers}}\n"
    )

    rendered = constitution.render_constitution_template(
        template,
        "agents",
        cfg_mgr,
        ["core"],
    )

    assert "- docs/A.md: Alpha" in rendered
    assert "- docs/B.md: Beta" in rendered
    assert "Src: core" in rendered
    # A real rule id from bundled registry should appear
    rules = constitution.get_rules_for_role("agent")
    sample_id = rules[0]["id"]
    assert sample_id in rendered
    assert "{{" not in rendered, "Handlebars markers should be rendered away"

def test_generate_all_constitutions_creates_files(tmp_path: Path) -> None:
    repo_root = tmp_path
    core_const_dir = repo_root / ".edison" / "core" / "constitutions"
    core_const_dir.mkdir(parents=True, exist_ok=True)

    (core_const_dir / "orchestrator-base.md").write_text("ORCH", encoding="utf-8")
    (core_const_dir / "agents-base.md").write_text("AGENT", encoding="utf-8")
    (core_const_dir / "validators-base.md").write_text("VALID", encoding="utf-8")

    cfg_mgr = _make_config_manager(repo_root)
    output_root = repo_root / ".edison" / "_generated"

    constitution.generate_all_constitutions(cfg_mgr, output_root)

    out_dir = output_root / "constitutions"
    assert (out_dir / "ORCHESTRATORS.md").exists()
    assert (out_dir / "AGENTS.md").exists()
    assert (out_dir / "VALIDATORS.md").exists()

    assert "ORCH" in (out_dir / "ORCHESTRATORS.md").read_text(encoding="utf-8")
    assert "AGENT" in (out_dir / "AGENTS.md").read_text(encoding="utf-8")
    assert "VALID" in (out_dir / "VALIDATORS.md").read_text(encoding="utf-8")
