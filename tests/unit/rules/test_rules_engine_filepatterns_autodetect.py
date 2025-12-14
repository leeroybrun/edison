from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from edison.core.context.files import FileContextService
from edison.core.rules import RulesEngine
from edison.core.utils.patterns import matches_any_pattern


def test_rules_engine_filepatterns_match_with_autodetect(isolated_project_env: Path) -> None:
    """If a rule has filePatterns and changed_files=None, the engine should auto-detect.

    This verifies we did NOT remove the feature; we only made auto-detection lazy.
    """
    # Create an untracked file so `git status` sees it.
    target = isolated_project_env / "apps" / "dashboard" / "src" / "app" / "page.tsx"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("export default function Page() { return null }\n", encoding="utf-8")

    # Sanity: git-status based detection should see the untracked file.
    ctx = FileContextService(project_root=isolated_project_env).get_current()
    rel = "apps/dashboard/src/app/page.tsx"
    assert rel in ctx.all_files, f"Expected {rel} in detected files, got: {ctx.all_files}"
    assert matches_any_pattern(rel, ["apps/dashboard/**"]) is True

    cfg: Dict[str, Any] = {
        "rules": {
            "project": [
                {
                    "id": "RULE.TEST.FILEPATTERN",
                    "description": "Should match when dashboard files are touched",
                    "enforced": True,
                    "blocking": False,
                    "config": {
                        "contexts": [
                            {
                                "type": "validation",
                                "filePatterns": ["apps/dashboard/**"],
                                "priority": 10,
                            }
                        ]
                    },
                }
            ]
        }
    }

    engine = RulesEngine(cfg)
    rules = engine.get_rules_for_context("validation", changed_files=None)
    assert [r.id for r in rules] == ["RULE.TEST.FILEPATTERN"]


