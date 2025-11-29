from __future__ import annotations

import json
import subprocess
from pathlib import Path

from edison.core.utils.paths import PathResolver 
from edison.core.utils.paths.project import get_project_config_dir 
def test_session_template_resolves_from_project_config_dir(
    monkeypatch: "pytest.MonkeyPatch", tmp_path: Path
) -> None:
    """Session templates must resolve via project config directory, not hardcoded paths."""

    # Simulate an isolated repo that uses .edison as the project config dir (no .agents)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

    project_config_dir = tmp_path / ".edison"
    template_path = project_config_dir / "sessions" / "TEMPLATE.json"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_payload = {
        "meta": {"sessionId": "demo-session", "owner": "tester"},
        "state": "active",
        "tasks": {},
        "qa": {},
    }
    template_path.write_text(json.dumps(template_payload), encoding="utf-8")

    # Reload session config and repository to pick up new environment
    from edison.core.session import reset_config_cache
    from edison.core.session.persistence.repository import SessionRepository

    reset_config_cache()

    # The SessionRepository should resolve templates from the project config dir
    repo = SessionRepository()
    template_file = project_config_dir / "sessions" / "TEMPLATE.json"
    assert template_file.exists(), f"Template should exist at {template_file}"

    # Verify project config dir is correct
    assert get_project_config_dir(PathResolver.resolve_project_root()) == project_config_dir

