from __future__ import annotations

import json
from pathlib import Path

import pytest

from edison.core.adapters import PalAdapter, WORKFLOW_HEADING
from edison.core.config import ConfigManager
from tests.helpers.paths import get_repo_root


def _cli_roles_and_paths(repo_root: Path) -> list[tuple[str, Path]]:
    """Return (role, prompt_path) pairs for project CLI roles."""
    cli_dir = repo_root / ".pal" / "conf" / "cli_clients"
    if not cli_dir.exists():
        pytest.skip("Pal CLI client config directory missing")

    roles: list[tuple[str, Path]] = []
    for cfg_path in cli_dir.glob("*.json"):
        data = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
        for role_name, spec in (data.get("roles") or {}).items():
            if not isinstance(spec, dict):
                continue
            if not role_name.startswith("project-"):
                continue
            prompt_rel = spec.get("prompt_path")
            if not isinstance(prompt_rel, str):
                continue
            prompt_path = (cfg_path.parent / prompt_rel).resolve()
            roles.append((role_name, prompt_path))
    return roles


def test_verify_cli_prompts_syncs_all_project_roles(isolated_project_env: Path) -> None:
    """
    PalAdapter.verify_cli_prompts should ensure all CLI project roles
    have prompt files that include the workflow loop section.
    """
    repo_root = isolated_project_env
    cfg = ConfigManager(repo_root).load_config(validate=False)
    adapter = PalAdapter(project_root=repo_root, config=cfg)

    report = adapter.verify_cli_prompts(sync=True)

    # Basic shape
    assert isinstance(report, dict)
    assert report.get("ok") is True, f"Expected CLI prompt verification to succeed: {report}"

    roles = _cli_roles_and_paths(repo_root)
    assert roles, "No project roles discovered in CLI client configs"

    missing = report.get("missing") or []
    missing_workflow = report.get("missingWorkflow") or []
    assert not missing, f"Missing prompt files: {missing}"
    assert not missing_workflow, f"Missing workflow loop in prompts: {missing_workflow}"

    # Double-check on disk for safety
    for role_name, path in roles:
        assert path.exists(), f"Prompt file missing for {role_name}: {path}"
        text = path.read_text(encoding="utf-8")
        assert WORKFLOW_HEADING in text, f"Workflow loop not found in {path}"
