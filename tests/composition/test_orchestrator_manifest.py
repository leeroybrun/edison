import json
import pytest
from pathlib import Path

from edison.core.composition.orchestrator import compose_orchestrator_manifest

def test_compose_orchestrator_manifest_integration(tmp_path):
    """
    Integration test for compose_orchestrator_manifest using real file system.
    
    Verifies that the orchestrator manifest is correctly assembled from:
    - Agents (core + packs + project)
    - Validators (config)
    - Guidelines (core + packs)
    - Delegation config
    """
    # --- Setup File System ---
    repo_root = tmp_path
    edison_dir = repo_root / ".edison"
    core_dir = edison_dir / "core"
    packs_dir = edison_dir / "packs"
    project_dir = repo_root  # Project root is repo root for this test
    output_dir = repo_root / "output"
    
    # Create directories
    (core_dir / "agents").mkdir(parents=True)
    (core_dir / "guidelines").mkdir(parents=True)
    (core_dir / "delegation").mkdir(parents=True)
    (packs_dir / "testpack" / "agents").mkdir(parents=True)
    (packs_dir / "testpack" / "guidelines").mkdir(parents=True)
    (project_dir / "delegation").mkdir(parents=True)
    
    # 1. Create Core Agent
    (core_dir / "agents" / "generic-core.md").write_text("# Agent: Generic", encoding="utf-8")
    
    # 2. Create Pack Agent (Overlay)
    (packs_dir / "testpack" / "agents" / "generic.md").write_text("## Tools\npack tool", encoding="utf-8")
    
    # 3. Create Pack Metadata
    (packs_dir / "testpack" / "pack.yml").write_text("pack:\n  id: testpack\n  name: Test Pack", encoding="utf-8")
    
    # 4. Create Mandatory Guidelines
    (core_dir / "guidelines" / "SESSION_WORKFLOW.md").write_text("# Workflow", encoding="utf-8")
    (core_dir / "guidelines" / "DELEGATION.md").write_text("# Delegation", encoding="utf-8")
    (core_dir / "guidelines" / "TDD.md").write_text("# TDD", encoding="utf-8")
    
    # 5. Create Pack Guideline
    (packs_dir / "testpack" / "guidelines" / "PACK_RULE.md").write_text("# Pack Rule", encoding="utf-8")
    
    # 6. Create Delegation Config
    (core_dir / "delegation" / "config.json").write_text(
        json.dumps({"priority": {"implementers": ["generic"]}})
        , 
        encoding="utf-8"
    )
    
    # --- Run Composition ---
    config = {
        "validation": {
            "roster": {
                "global": [{"id": "val-1", "name": "Validator 1"}]
            }
        },
        "validators": {
            "roster": {
                "global": [{"id": "val-1", "alwaysRun": True}] # Override
            }
        }
    }
    
    result = compose_orchestrator_manifest(
        config=config,
        repo_root=repo_root,
        core_dir=core_dir,
        packs_dir=packs_dir,
        project_dir=project_dir,
        active_packs=["testpack"],
        output_dir=output_dir
    )
    
    # --- Verify Output ---
    
    # Check result dict
    assert "json" in result
    json_file = result["json"]
    assert json_file.exists()
    assert json_file.parent == output_dir
    
    # Check JSON content
    data = json.loads(json_file.read_text(encoding="utf-8"))
    
    # 1. Verify Metadata
    assert data["version"] == "2.0.0"
    assert "generated" in data
    
    # 2. Verify Packs
    assert len(data["packs"]) == 1
    assert data["packs"][0]["id"] == "testpack"
    assert data["packs"][0]["name"] == "Test Pack"
    
    # 3. Verify Agents
    # generic should be in specialized because it has a pack overlay
    assert "generic" in data["agents"]["specialized"]
    
    # 4. Verify Validators (merged)
    assert len(data["validators"]["global"]) == 1
    val = data["validators"]["global"][0]
    assert val["id"] == "val-1"
    assert val["alwaysRun"] is True
    
    # 5. Verify Guidelines
    guidelines = data["guidelines"]
    files = [g["file"] for g in guidelines]
    assert ".edison/core/guidelines/SESSION_WORKFLOW.md" in files
    assert any("PACK_RULE.md" in f for f in files)
    
    # 6. Verify Delegation
    assert "generic" in data["delegation"]["priority"]["implementers"]
    
    # 7. Verify Workflow Loop (defaults used as no config file)
    assert "command" in data["workflowLoop"]
