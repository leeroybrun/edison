from __future__ import annotations

from pathlib import Path

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


def test_file_store_provider_writes_session_insights_artifact(isolated_project_env: Path) -> None:
    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "memory.yaml",
        {
            "memory": {
                "enabled": True,
                "providers": {
                    "file": {"kind": "file-store", "enabled": True},
                },
            }
        },
    )
    reset_edison_caches()

    from edison.core.memory import MemoryManager

    mgr = MemoryManager(project_root=isolated_project_env)
    mgr.save_structured(  # type: ignore[attr-defined]
        {
            "schema": "session-insights-v1",
            "sessionId": "sess-1",
            "discoveries": {
                "patterns_found": ["Prefer repository methods over ad-hoc IO"],
                "gotchas_encountered": ["Config validation is strict"],
                "files_understood": {"src/app.py": "entrypoint"},
            },
        },
        session_id="sess-1",
    )

    insights_path = isolated_project_env / ".project" / "memory" / "session_insights" / "sess-1.json"
    assert insights_path.exists()
    text = insights_path.read_text(encoding="utf-8")
    assert "session-insights-v1" in text
    assert "sess-1" in text

