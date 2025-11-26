
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from edison.core.composition.orchestrator import compose_orchestrator_manifest

def test_compose_orchestrator_manifest_json_output(tmp_path):
    """Verify that orchestrator manifest JSON is written correctly."""
    output_dir = tmp_path / "output"
    
    # Mock dependencies to avoid complex setup
    with patch("edison.core.composition.orchestrator.collect_validators") as mock_val, \
         patch("edison.core.composition.orchestrator.collect_agents") as mock_agents, \
         patch("edison.core.composition.orchestrator.collect_packs") as mock_packs, \
         patch("edison.core.composition.orchestrator.collect_mandatory_guidelines") as mock_mg, \
         patch("edison.core.composition.orchestrator.collect_role_guidelines") as mock_rg, \
         patch("edison.core.composition.orchestrator.load_delegation_config") as mock_del, \
         patch("edison.core.composition.orchestrator.get_workflow_loop_instructions") as mock_wfl, \
         patch("edison.core.composition.orchestrator.render_orchestrator_markdown") as mock_md_render, \
         patch("edison.core.composition.orchestrator.render_orchestrator_json") as mock_json_render:
        
        mock_val.return_value = {}
        mock_agents.return_value = {}
        mock_packs.return_value = []
        mock_mg.return_value = []
        mock_rg.return_value = {}
        mock_del.return_value = {}
        mock_wfl.return_value = "Loop"
        mock_md_render.return_value = "# Guide"
        # This is the content we expect to see written
        mock_json_render.return_value = {"test": "value", "foo": "bar"}
        
        compose_orchestrator_manifest(
            config={},
            repo_root=Path("/repo"),
            core_dir=tmp_path / "core",
            packs_dir=tmp_path / "packs",
            project_dir=tmp_path / "project",
            active_packs=[],
            output_dir=output_dir
        )
        
        json_file = output_dir / "orchestrator-manifest.json"
        assert json_file.exists()
        
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert data == {"test": "value", "foo": "bar"}
        
        # Verify indentation (check raw text)
        text = json_file.read_text(encoding="utf-8")
        assert '  "test": "value"' in text or '  "test":' in text
