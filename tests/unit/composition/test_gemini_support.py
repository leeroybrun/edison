from __future__ import annotations

from pathlib import Path
import sys
import os


# Resolve repository root and ensure Edison core is importable
ROOT = Path(__file__).resolve().parents[5]
CORE_PATH = ROOT / ".edison" / "core"
if str(CORE_PATH) not in sys.path:
# Force repo-root resolution to the outer project, not the nested .edison git repo.
os.environ.setdefault("AGENTS_PROJECT_ROOT", str(ROOT))

from edison.core.composition import CompositionEngine 
from edison.core.paths.project import get_project_config_dir 
from edison.core.config import ConfigManager 
class TestGeminiSupport:
    def test_gemini_global_in_validation_roster(self) -> None:
        """gemini-global must be present in validation.roster.global."""
        cfg = ConfigManager(repo_root=ROOT).load_config(validate=False)
        global_validators = (cfg.get("validation", {}) or {}).get("roster", {}).get("global", []) or []

        gemini_validator = next(
            (v for v in global_validators if v.get("id") == "gemini-global"),
            None,
        )

        assert gemini_validator is not None, "gemini-global not found in validation.roster.global"
        assert gemini_validator.get("model") == "gemini"
        assert gemini_validator.get("alwaysRun") is True
        assert gemini_validator.get("specFile") == ".cache/composed/gemini-global.md"

    def test_gemini_core_template_exists(self) -> None:
        """Core validator template for Gemini must exist and mention key requirements."""
        gemini_core = CORE_PATH / "validators" / "global" / "gemini-core.md"
        assert gemini_core.exists(), "gemini-core.md template not found"

        content = gemini_core.read_text(encoding="utf-8")
        assert "# Gemini Global Validator (Core)" in content
        assert "validator-report.schema.json" in content
        assert "Long context" in content  # Gemini-specific strength

    def test_composition_generates_gemini_global(self) -> None:
        """Composition engine must generate a composed gemini-global validator prompt."""
        engine = CompositionEngine(repo_root=ROOT)
        results = engine.compose_validators(validator="all")

        assert "gemini-global" in results, "compose_validators('all') must include gemini-global"

        res = results["gemini-global"]
        assert res.cache_path is not None
        assert res.cache_path.name == "gemini-global.md"
        expected_project_dir = get_project_config_dir(ROOT)
        assert res.cache_path.parent == expected_project_dir / ".cache" / "composed"
        assert res.cache_path.exists()

        content = res.cache_path.read_text(encoding="utf-8")
        assert "Gemini" in content
