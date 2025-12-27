from __future__ import annotations

from pathlib import Path

from edison.core.state.loader import load_guards
from edison.core.state.guards import registry as guard_registry


def test_company_layer_can_provide_state_guards(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    company_dir = root / "company-layer"
    (company_dir / "config").mkdir(parents=True)

    guards_dir = company_dir / "guards"
    guards_dir.mkdir(parents=True, exist_ok=True)
    (guards_dir / "company_guard.py").write_text(
        "from __future__ import annotations\n"
        "from typing import Mapping, Any\n\n"
        "def company_guard(context: Mapping[str, Any]) -> bool:\n"
        "    return True\n",
        encoding="utf-8",
    )

    proj_cfg = root / ".edison" / "config"
    proj_cfg.mkdir(parents=True, exist_ok=True)
    (proj_cfg / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company_dir.as_posix()}\n"
        "      before: user\n",
        encoding="utf-8",
    )

    # Ensure a clean registry so the test is deterministic.
    guard_registry.reset()

    load_guards(project_root=root, active_packs=[])
    assert guard_registry.has("company_guard")

