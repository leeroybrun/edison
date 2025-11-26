
import json
import shutil
import tempfile
from pathlib import Path
import pytest

from edison.core.composition import composers, includes
from edison.core.utils.paths import project

def test_compose_prompt_json_safe_refactor():
    # Setup temporary directory
    tmp_dir = Path(tempfile.mkdtemp())
    repo_root = tmp_dir
    
    # Override repo root for isolation
    includes._REPO_ROOT_OVERRIDE = repo_root
    
    # Use .edison as per default config
    project_dir = repo_root / ".edison"
    project_dir.mkdir(parents=True)
    
    # Create necessary files
    const_dir = project_dir / "_generated" / "constitutions"
    const_dir.mkdir(parents=True)
    (const_dir / "VALIDATORS.md").write_text("# Constitution\n\nRules.", encoding="utf-8")
    
    core_file = repo_root / "core.md"
    core_file.write_text("# Core Edison Principles\n\nThis is the core text.\nRepeated text to trigger DRY if needed but we force report anyway.", encoding="utf-8")
    
    try:
        composers.compose_prompt(
            validator_id="test-val",
            core_base=core_file,
            pack_contexts=[],
            overlay=None,
            enforce_dry=True
        )
    except Exception as e:
        pytest.fail(f"compose_prompt raised exception: {e}")
        
    # Check if report exists
    report_path = project_dir / "_generated" / "validators" / "duplication-reports" / "test-val.json"
    assert report_path.exists(), "Duplicate report JSON file should exist"
    
    # Check content for sorted keys
    content = report_path.read_text(encoding="utf-8")
    
    # Find indices of keys
    idx_counts = content.find('"counts"')
    idx_engine = content.find('"engineVersion"')
    
    assert idx_counts != -1
    assert idx_engine != -1
    
    # Assert keys are sorted (counts comes before engineVersion)
    assert idx_counts < idx_engine, "Keys should be sorted (counts before engineVersion)"

    # Cleanup
    shutil.rmtree(tmp_dir)
    includes._REPO_ROOT_OVERRIDE = None
