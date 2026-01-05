from __future__ import annotations

import json
from pathlib import Path

from edison.core.adapters import PalAdapter
from tests.helpers.io_utils import write_yaml


def test_pal_cli_clients_inject_mcp_overrides_for_validator_role(
    isolated_project_env: Path,
) -> None:
    repo_root = isolated_project_env

    # Ensure the e2e-web pack is active so the validator config + MCP server catalog are present.
    write_yaml(
        repo_root / ".edison" / "config" / "packs.yaml",
        {"packs": {"active": ["python", "e2e-web"]}},
    )

    # Provide a generated validator prompt so PalAdapter emits a validator role.
    gen_validators = repo_root / ".edison" / "_generated" / "validators"
    gen_validators.mkdir(parents=True, exist_ok=True)
    (gen_validators / "browser-e2e.md").write_text("# Browser E2E\n", encoding="utf-8")

    adapter = PalAdapter(project_root=repo_root)
    adapter.sync_all()

    cfg_path = repo_root / ".pal" / "conf" / "cli_clients" / "codex.json"
    data = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")

    role = (data.get("roles") or {}).get("validator-browser-e2e") or {}
    role_args = role.get("role_args") or []

    assert "-c" in role_args
    assert any(v.startswith("mcp_servers.playwright.command=") for v in role_args)
    assert any(v.startswith("mcp_servers.playwright.args=") for v in role_args)

