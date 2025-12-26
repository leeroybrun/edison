from __future__ import annotations

from pathlib import Path

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


def test_memory_pipeline_session_end_saves_structured_insights(isolated_project_env: Path) -> None:
    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "memory.yaml",
        {
            "memory": {
                "enabled": True,
                "providers": {"file": {"kind": "file-store", "enabled": True}},
                "pipelines": {
                    "session-end": {
                        "enabled": True,
                        "steps": [
                            {"id": "extract", "kind": "session-insights-v1", "outputVar": "insights"},
                            {
                                "id": "save",
                                "kind": "provider-save-structured",
                                "provider": "file",
                                "inputVar": "insights",
                            },
                        ],
                    }
                },
            }
        },
    )
    reset_edison_caches()

    from edison.core.memory.pipeline import run_memory_pipelines

    run_memory_pipelines(project_root=isolated_project_env, event="session-end", session_id="sess-1")

    path = isolated_project_env / ".project" / "memory" / "session_insights" / "sess-1.json"
    assert path.exists()

