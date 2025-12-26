from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


def test_memory_manager_supports_external_cli_text_provider(
    isolated_project_env: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Create a fake `episodic-memory` binary on PATH.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / "episodic-memory"
    fake.write_text("#!/usr/bin/env bash\necho \"FAKE_SEARCH_RESULT\"\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | 0o111)

    monkeypatch.setenv("PATH", os.pathsep.join([str(bin_dir), os.environ.get("PATH", "")]))

    # Enable memory + provider via project config override.
    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "memory.yaml",
        {
            "memory": {
                "enabled": True,
                "defaults": {"maxHits": 3},
                "providers": {
                    "episodic": {
                        "kind": "external-cli-text",
                        "enabled": True,
                        "command": "episodic-memory",
                        "searchArgs": ["search", "{query}"],
                        "timeoutSeconds": 2,
                    }
                },
            }
        },
    )
    reset_edison_caches()

    from edison.core.memory import MemoryManager

    mgr = MemoryManager(project_root=isolated_project_env)
    hits = mgr.search("hello", limit=2)
    assert len(hits) == 1
    assert "FAKE_SEARCH_RESULT" in hits[0].text
