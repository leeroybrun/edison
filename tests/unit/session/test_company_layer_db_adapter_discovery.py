from __future__ import annotations

from pathlib import Path

from edison.core.session.persistence.database import _load_database_adapter_module


def test_company_layer_can_provide_db_adapter_module(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    company_dir = root / "company-layer"
    (company_dir / "config").mkdir(parents=True)

    adapter_dir = company_dir / "packs" / "companydb" 
    adapter_dir.mkdir(parents=True, exist_ok=True)
    (adapter_dir / "db_adapter.py").write_text(
        "from __future__ import annotations\n\n"
        "def create_session_database(*, session_id: str, db_prefix: str, base_db_url: str, repo_dir):\n"
        "    return f\"sqlite:///{session_id}.db\"\n",
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

    mod = _load_database_adapter_module({"adapter": "companydb"})
    assert mod is not None
    assert hasattr(mod, "create_session_database")

