from __future__ import annotations

from pathlib import Path

from edison.core.config import ConfigManager
from edison.core.config.cache import get_cached_config
from edison.core.config.cache import clear_all_caches


def test_config_manager_load_config_is_centrally_cached(tmp_path: Path) -> None:
    """
    ConfigManager.load_config() should return the centrally cached config so repeated
    calls do not re-read YAML from disk unless caches are cleared.
    """
    clear_all_caches()
    try:
        cfg_dir = tmp_path / ".edison" / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)

        cfg_file = cfg_dir / "project.yaml"
        cfg_file.write_text("project:\n  name: first\n", encoding="utf-8")

        mgr = ConfigManager(tmp_path)
        cfg1 = mgr.load_config(validate=False)

        # Mutate on disk; cached config should not change until caches cleared.
        cfg_file.write_text("project:\n  name: second\n", encoding="utf-8")
        cfg2 = mgr.load_config(validate=False)

        assert cfg1 is cfg2, "Cached config should return the same dict instance"
        assert cfg2.get("project", {}).get("name") == "first"

        clear_all_caches()
        cfg3 = mgr.load_config(validate=False)
        assert cfg3.get("project", {}).get("name") == "second"
    finally:
        clear_all_caches()


def test_get_cached_config_default_repo_root_key_tracks_resolved_project_root(tmp_path: Path) -> None:
    """`get_cached_config(repo_root=None)` must not collapse multiple projects into one cache entry.

    The config cache key must reflect the resolved project root (via PathResolver)
    so switching `AGENTS_PROJECT_ROOT` within a single process yields distinct configs.
    """
    import os

    clear_all_caches()
    old_env = os.environ.get("AGENTS_PROJECT_ROOT")
    try:
        root1 = tmp_path / "proj1"
        root2 = tmp_path / "proj2"
        (root1 / ".edison" / "config").mkdir(parents=True, exist_ok=True)
        (root2 / ".edison" / "config").mkdir(parents=True, exist_ok=True)

        (root1 / ".edison" / "config" / "project.yaml").write_text(
            "project:\n  name: one\n", encoding="utf-8"
        )
        (root2 / ".edison" / "config" / "project.yaml").write_text(
            "project:\n  name: two\n", encoding="utf-8"
        )

        os.environ["AGENTS_PROJECT_ROOT"] = str(root1)
        cfg1 = get_cached_config(repo_root=None, validate=False)
        assert cfg1.get("project", {}).get("name") == "one"

        # Switch project root in the same process; must not reuse the prior cache entry.
        os.environ["AGENTS_PROJECT_ROOT"] = str(root2)
        cfg2 = get_cached_config(repo_root=None, validate=False)
        assert cfg2.get("project", {}).get("name") == "two"
        assert cfg1 is not cfg2
    finally:
        clear_all_caches()
        if old_env is None:
            os.environ.pop("AGENTS_PROJECT_ROOT", None)
        else:
            os.environ["AGENTS_PROJECT_ROOT"] = old_env

