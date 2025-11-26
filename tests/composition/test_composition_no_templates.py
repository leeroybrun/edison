from __future__ import annotations

import shutil
from pathlib import Path

from edison.core.composition import CompositionEngine
from edison.core.paths.project import get_project_config_dir

# ROOT points to the edison project root for copying test data
ROOT = Path(__file__).resolve().parents[2]


def test_composition_works_without_templates_dir(isolated_project_env: Path) -> None:
    """CompositionEngine must not depend on a validators/templates directory."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)

    # Copy validators directory structure to isolated environment
    # CompositionEngine looks in {project_dir}/core/validators
    src_validators = ROOT / "src" / "edison" / "data" / "validators"
    dst_validators = project_dir / "core" / "validators"
    if src_validators.exists():
        dst_validators.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_validators, dst_validators, dirs_exist_ok=True)

    # Set repo root override for composition modules to use isolated env
    import edison.core.composition.includes as includes
    import edison.core.composition.composers as composers
    includes._REPO_ROOT_OVERRIDE = root
    composers._REPO_ROOT_OVERRIDE = root

    engine = CompositionEngine(repo_root=root)

    # Compose global validators - all three use the same prompt (global.md)
    # but run on different models for multiple perspectives
    results = {}
    for validator in ["global-codex", "global-claude", "global-gemini"]:
        result = engine.compose_validators(validator=validator, packs_override=[])
        results.update(result)

    # All three validators should be in results, sharing the same composed prompt
    assert "global-codex" in results
    assert "global-claude" in results
    assert "global-gemini" in results
    
    # Verify cache exists and is in isolated environment
    for key, res in results.items():
        assert res.cache_path is not None
        assert res.cache_path.exists()
        # Verify cache is in isolated environment, not Edison repo
        assert root in res.cache_path.parents, f"Cache path {res.cache_path} not in isolated env {root}"
    
    # All three should point to the same composed file (global.md, not global-codex.md)
    cache_paths = {res.cache_path for res in results.values()}
    assert len(cache_paths) == 1, "All global validators should share the same composed prompt"
