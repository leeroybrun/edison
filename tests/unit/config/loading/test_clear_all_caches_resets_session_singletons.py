from __future__ import annotations

from pathlib import Path

import pytest

from helpers.io_utils import write_yaml


def test_clear_all_caches_resets_session_config_singleton(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`clear_all_caches()` should be sufficient to refresh all config consumers.

    Session config currently uses a cached singleton accessor (`edison.core.session._config.get_config`).
    Clearing the central config cache must also invalidate that singleton; otherwise config refresh
    becomes fragmented (some callers must remember to clear multiple caches).
    """
    repo_root = tmp_path / "proj"
    cfg_dir = repo_root / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo_root))

    from edison.core.config.cache import clear_all_caches
    from edison.core.session._config import get_config

    # Initial config
    write_yaml(
        cfg_dir / "session.yaml",
        {
            "session": {
                "paths": {"root": ".project/sessions-v1", "archive": ".project/archive", "tx": ".project/tx"},
                "states": {"active": "active"},
                "lookupOrder": ["active"],
                "validation": {"idRegex": r"^[a-zA-Z0-9_\\-\\.]+$", "maxLength": 100},
            }
        },
    )
    clear_all_caches()
    cfg1 = get_config()
    assert cfg1.get_session_root_path() == ".project/sessions-v1"

    # Change on disk; clearing *central* caches must be enough to see the update.
    write_yaml(
        cfg_dir / "session.yaml",
        {
            "session": {
                "paths": {"root": ".project/sessions-v2", "archive": ".project/archive", "tx": ".project/tx"},
                "states": {"active": "active"},
                "lookupOrder": ["active"],
                "validation": {"idRegex": r"^[a-zA-Z0-9_\\-\\.]+$", "maxLength": 100},
            }
        },
    )
    clear_all_caches()
    cfg2 = get_config()
    assert cfg2.get_session_root_path() == ".project/sessions-v2"









