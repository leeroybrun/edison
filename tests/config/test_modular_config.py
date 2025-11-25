from __future__ import annotations
from pathlib import Path
import pytest
import sys

# Locate core root to import ConfigManager
_cur = Path(__file__).resolve()
ROOT: Path | None = None
CORE_ROOT: Path | None = None
parents = list(_cur.parents)
for cand in parents:
    if (cand / ".edison" / "core" / "lib" / "config.py").exists():
        ROOT = cand
        CORE_ROOT = cand / ".edison" / "core"
        break

if ROOT:
    from edison.core.config import ConfigManager
else:
    pytest.fail("Cannot locate Edison core root")

def test_modular_config_loading(tmp_path: Path) -> None:
    """
    Verify that ConfigManager loads configuration from the new modular 
    .edison/core/config/ structure and merges it correctly.
    """
    # Setup modular config structure
    core_config_dir = tmp_path / ".edison" / "core" / "config"
    core_config_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. defaults.yaml
    (core_config_dir / "defaults.yaml").write_text("""
edison:
  version: "2.0.0"
git:
  branchPrefix: "feature/"
""", encoding="utf-8")

    # 2. validators.yaml
    (core_config_dir / "validators.yaml").write_text("""
validation:
  roster:
    global:
      - id: test-validator
""", encoding="utf-8")

    # 3. delegation.yaml
    (core_config_dir / "delegation.yaml").write_text("""
delegation:
  implementers:
    primary: codex
""", encoding="utf-8")

    # 4. models.yaml
    (core_config_dir / "models.yaml").write_text("""
models:
  codex:
    provider: zen-mcp
""", encoding="utf-8")
    
    # 5. packs.yaml
    (core_config_dir / "packs.yaml").write_text("""
packs:
  enabled: true
""", encoding="utf-8")
    
    # 6. state-machine.yaml
    (core_config_dir / "state-machine.yaml").write_text("""
statemachine:
  task:
    states:
      todo:
        description: "backlog"
        allowed_transitions:
          - to: done
      done:
        final: true
        allowed_transitions: []
""", encoding="utf-8")

    # Create project overlay under .agents/config (canonical overlays path)
    agents_config_dir = tmp_path / ".agents" / "config"
    agents_config_dir.mkdir(parents=True, exist_ok=True)
    (agents_config_dir / "project.yml").write_text("project: { name: test }", encoding="utf-8")
    
    # Initialize ConfigManager
    mgr = ConfigManager(tmp_path)
    
    # Force it to use the new path structure (simulating the change we need to make)
    # Note: We can't easily mock internal attributes if we want to test the __init__ logic logic changes,
    # so we rely on the ConfigManager logic we ARE ABOUT TO WRITE.
    # Ideally, we want ConfigManager to *automatically* detect or prefer core/config if we change the code.
    
    cfg = mgr.load_config(validate=False)
    
    # Assertions
    assert cfg.get("edison", {}).get("version") == "2.0.0"
    assert cfg.get("git", {}).get("branchPrefix") == "feature/"
    
    # Check merged modules
    assert "validation" in cfg
    assert cfg["validation"]["roster"]["global"][0]["id"] == "test-validator"
    
    assert "delegation" in cfg
    assert cfg["delegation"]["implementers"]["primary"] == "codex"
    
    assert "models" in cfg
    assert cfg["models"]["codex"]["provider"] == "zen-mcp"
    
    assert "packs" in cfg
    assert cfg["packs"]["enabled"] is True
    
    assert "statemachine" in cfg
    task_states = cfg["statemachine"]["task"]["states"]
    assert set(task_states.keys()) == {"todo", "done"}
    assert task_states["todo"]["allowed_transitions"][0]["to"] == "done"

def test_no_json_fallback(tmp_path: Path) -> None:
    """Ensure JSON config files are ignored in the new structure."""
    core_config_dir = tmp_path / ".edison" / "core" / "config"
    core_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Write a JSON file that should be IGNORED
    (core_config_dir / "ignored.json").write_text('{"should_ignore": true}', encoding="utf-8")
    
    # Write minimal defaults
    (core_config_dir / "defaults.yaml").write_text("edison: { version: '1.0' }", encoding="utf-8")
    
    agents_config_dir = tmp_path / ".agents" / "config"
    agents_config_dir.mkdir(parents=True, exist_ok=True)
    (agents_config_dir / "project.yml").write_text("project: { name: test }", encoding="utf-8")

    mgr = ConfigManager(tmp_path)
    cfg = mgr.load_config(validate=False)
    
    assert "should_ignore" not in cfg


def test_legacy_monolithic_project_config_yml_is_ignored(tmp_path: Path) -> None:
    """
    Ensure legacy .agents/config.yml is ignored in favour of .agents/config/*.yml overlays.
    """
    # Core defaults
    core_config_dir = tmp_path / ".edison" / "core" / "config"
    core_config_dir.mkdir(parents=True, exist_ok=True)
    (core_config_dir / "defaults.yaml").write_text(
        "git:\n  branchPrefix: 'from-defaults/'\n", encoding="utf-8"
    )

    # Legacy monolithic config.yml (must NOT be loaded)
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "config.yml").write_text(
        "git: { branchPrefix: 'from-config-yml/', legacyOnlyKey: true }\n", encoding="utf-8"
    )

    # Canonical overlay under .agents/config/*.yml
    agents_config_dir = agents_dir / "config"
    agents_config_dir.mkdir(parents=True, exist_ok=True)
    (agents_config_dir / "project.yml").write_text(
        "git: { branchPrefix: 'from-overlay/' }\n", encoding="utf-8"
    )

    mgr = ConfigManager(tmp_path)
    cfg = mgr.load_config(validate=False)

    # Overlay must win; legacy-only key from config.yml must not be merged.
    assert cfg.get("git", {}).get("branchPrefix") == "from-overlay/"
    assert "legacyOnlyKey" not in cfg.get("git", {})

def test_project_modular_config_loading(tmp_path: Path) -> None:
    """
    Verify that ConfigManager loads project-level modular config from 
    .agents/config/ and merges it on top of core defaults.
    """
    # Setup core config
    core_config_dir = tmp_path / ".edison" / "core" / "config"
    core_config_dir.mkdir(parents=True, exist_ok=True)
    (core_config_dir / "defaults.yaml").write_text("edison: { version: '1.0' }", encoding="utf-8")
    
    # Setup project config dir (canonical overlays under .agents/config)
    project_config_dir = tmp_path / ".agents" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)

    # Create a project-level metadata overlay
    (project_config_dir / "project.yml").write_text(
        "project: { name: test }\n", encoding="utf-8"
    )

    # Create a project-specific validator overlay
    (project_config_dir / "validators.yml").write_text("""
validation:
  roster:
    project_specific:
      - id: project-validator
""", encoding="utf-8")

    # Create a project-specific delegation overlay
    (project_config_dir / "delegation.yml").write_text("""
delegation:
  implementers:
    primary: claude
""", encoding="utf-8")
    
    mgr = ConfigManager(tmp_path)
    cfg = mgr.load_config(validate=False)
    
    # Check core loaded
    assert cfg["edison"]["version"] == "1.0"

    # Check project overlay loaded
    assert cfg["project"]["name"] == "test"

    # Check modular project config loaded
    assert "project_specific" in cfg["validation"]["roster"]
    assert cfg["validation"]["roster"]["project_specific"][0]["id"] == "project-validator"
    
    # Check override
    assert cfg["delegation"]["implementers"]["primary"] == "claude"

def test_core_repo_config_validates_against_canonical_schema() -> None:
    """
    Real repository config (.edison/core/config + .agents/config.yml) must
    validate against the canonical Draft-2020-12 config schema.
    """
    import json
    from jsonschema import Draft202012Validator, ValidationError

    assert ROOT is not None
    mgr = ConfigManager(ROOT)
    cfg = mgr.load_config(validate=False)

    schema_path = Path(".edison/core/schemas/config.schema.json")
    assert schema_path.exists(), "Missing core config schema: .edison/core/schemas/config.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    try:
        Draft202012Validator(schema).validate(cfg)
    except ValidationError as exc:  # pragma: no cover - would indicate schema drift
        pytest.fail(f"Canonical config schema rejected real repo config: {exc}")
