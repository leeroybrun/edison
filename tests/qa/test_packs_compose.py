from __future__ import annotations

from pathlib import Path
import json
import os

from edison.core.packs import compose_from_file 
def test_compose_latest_wins_and_order():
    cfg = Path.cwd() / "core" / "tests" / "fixtures" / "pack-scenarios" / "edison.nextjs-react.yaml"

    # Force pack resolution to project root so pack directories resolve correctly when tests run inside .edison
    os.environ["AGENTS_PROJECT_ROOT"] = str(Path.cwd().parent)
    result = compose_from_file(cfg, strategy="latest-wins")

    # basic shape
    assert set(result.keys()) >= {"packs", "loadOrder", "dependencies", "devDependencies", "scripts", "conflicts"}

    # load order respects required packs (e.g., typescript before react/nextjs)
    order = result["loadOrder"]
    assert order.index("typescript") < order.index("react")
    assert order.index("react") < order.index("nextjs")

    # versions present per approval
    deps = result["dependencies"]
    dev = result["devDependencies"]
    assert deps.get("react") == "^19.0.0"
    assert deps.get("next") == "^16.0.0"
    assert dev.get("typescript") == "^5.7.2" or deps.get("typescript") == "^5.7.2"
