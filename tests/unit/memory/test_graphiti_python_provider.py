from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


def test_memory_manager_supports_graphiti_python_provider(
    isolated_project_env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Provide a fake `graphiti_memory` Python module on sys.path.
    mod_dir = tmp_path / "py"
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "graphiti_memory.py").write_text(
        """
from __future__ import annotations

import os
from pathlib import Path


class GraphitiMemory:
    def __init__(self, spec_dir: Path, project_dir: Path, group_id_mode: str = "project"):
        self.is_enabled = True

    async def get_relevant_context(self, query: str, num_results: int = 5, include_project_context: bool = True):
        return [{"content": f"CTX:{query}", "score": 0.9, "type": "pattern"}]

    async def save_pattern(self, pattern: str) -> bool:
        out = os.environ.get("GRAPHITI_FAKE_OUT")
        if out:
            Path(out).write_text(pattern, encoding="utf-8")
        return True

    async def close(self) -> None:
        return None
""".lstrip(),
        encoding="utf-8",
    )

    sys.path.insert(0, str(mod_dir))
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(mod_dir), os.environ.get("PYTHONPATH", "")]))

    out_file = tmp_path / "graphiti_saved.txt"
    monkeypatch.setenv("GRAPHITI_FAKE_OUT", str(out_file))

    # Enable memory + graphiti provider via project config override.
    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "memory.yaml",
        {
            "memory": {
                "enabled": True,
                "defaults": {"maxHits": 5},
                "providers": {
                    "graphiti": {
                        "kind": "graphiti-python",
                        "enabled": True,
                        "module": "graphiti_memory",
                        "class": "GraphitiMemory",
                        "specDir": "{PROJECT_MANAGEMENT_DIR}/memory/graphiti",
                        "groupIdMode": "project",
                        "includeProjectContext": True,
                        "saveMethod": "save_pattern",
                        "saveTemplate": "{summary}",
                    }
                },
            }
        },
    )
    reset_edison_caches()

    from edison.core.memory import MemoryManager

    mgr = MemoryManager(project_root=isolated_project_env)
    hits = mgr.search("hello", limit=3)
    assert len(hits) == 1
    assert hits[0].provider_id == "graphiti"
    assert hits[0].text == "CTX:hello"
    assert hits[0].score == pytest.approx(0.9)

    mgr.save("SAVED_SUMMARY", session_id="sess-123")
    assert out_file.read_text(encoding="utf-8") == "SAVED_SUMMARY"

