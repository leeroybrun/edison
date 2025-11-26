from __future__ import annotations

import shutil
import sys
from pathlib import Path

from edison.core.composition import CompositionEngine

# ROOT points to the edison project root for copying test data
ROOT = Path(__file__).resolve().parents[2]


def test_composition_works_without_templates_dir(isolated_project_env: Path) -> None:
    """CompositionEngine must not depend on a validators/templates directory."""
    root = isolated_project_env

    # Copy validators directory structure to isolated environment
    # CompositionEngine looks in .edison/core/validators when .edison exists (which isolated_project_env creates)
    src_validators = ROOT / "src" / "edison" / "data" / "validators"
    dst_validators = root / ".edison" / "core" / "validators"
    if src_validators.exists():
        dst_validators.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_validators, dst_validators, dirs_exist_ok=True)

    # Set repo root override for composition modules to use isolated env
    import edison.core.composition.includes as includes
    import edison.core.composition.composers as composers
    includes._REPO_ROOT_OVERRIDE = root
    composers._REPO_ROOT_OVERRIDE = root

    engine = CompositionEngine(repo_root=root)

    # Compose each global validator individually to verify they work
    # (composing "all" tries to compose pack-dependent validators which don't exist in core)
    results = {}
    for validator in ["codex", "claude", "gemini"]:
        result = engine.compose_validators(validator=validator, packs_override=[])
        results.update(result)

    assert "codex-global" in results
    assert "claude-global" in results
    assert "gemini-global" in results
    for res in results.values():
        assert res.cache_path is not None
        assert res.cache_path.exists()
        # Verify cache is in isolated environment, not Edison repo
        assert root in res.cache_path.parents, f"Cache path {res.cache_path} not in isolated env {root}"
