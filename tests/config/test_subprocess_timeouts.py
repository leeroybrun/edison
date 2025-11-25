from __future__ import annotations

from pathlib import Path
import sys


# Locate Edison core root (mirrors other config tests)
_cur = Path(__file__).resolve()
ROOT: Path | None = None
for cand in _cur.parents:
    if (cand / ".edison" / "core" / "lib" / "config.py").exists():
        ROOT = cand
        break

assert ROOT is not None

from edison.core.config import ConfigManager 
def test_subprocess_timeouts_defaults_present() -> None:
    cfg = ConfigManager(ROOT).load_config(validate=False)
    timeouts = cfg.get("subprocess_timeouts") or {}

    assert timeouts.get("git_operations") == 30
    assert timeouts.get("test_execution") == 300
    assert timeouts.get("build_operations") == 600
    assert timeouts.get("ai_calls") == 120
    assert timeouts.get("file_operations") == 10
    assert timeouts.get("default") == 60
