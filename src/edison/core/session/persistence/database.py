"""Database isolation and management."""
from __future__ import annotations

import re
import importlib.util as _importlib_util
from typing import Any, Dict, Optional
from pathlib import Path

from edison.core.utils.paths import PathResolver
from edison.core.utils.paths import get_project_config_dir
from .._config import get_config, reset_config_cache


def _session_config():
    """Return the SessionConfig instance.
    
    Uses the centralized config accessor.
    """
    return get_config()


def _database_config() -> Dict[str, Any]:
    cfg = _session_config().get_database_config()
    return cfg if isinstance(cfg, dict) else {}


def _get_database_url(db_cfg: Optional[Dict[str, Any]] = None) -> str:
    """Return database.url sourced from the configuration system (env aliases supported)."""
    db_cfg = db_cfg or _database_config()
    url_raw = db_cfg.get("url") if isinstance(db_cfg, dict) else None
    if isinstance(url_raw, str) and url_raw.strip():
        return url_raw.strip()

    raise ValueError(
        "database.url must be configured when database.enabled is true; set EDISON_database__url "
        "(preferred) or DATABASE_URL (legacy). No default is provided for security reasons."
    )


def _get_session_db_prefix(db_cfg: Optional[Dict[str, Any]] = None) -> str:
    """Return the configured session DB prefix from project config."""
    db_cfg = db_cfg or _database_config()
    prefix = db_cfg.get("sessionPrefix")
    if not prefix:
        raise ValueError(
            "Missing configuration: database.sessionPrefix in project config (config.yml or defaults)."
        )
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(prefix)):
        raise ValueError(
            "Invalid database.sessionPrefix: must start with a letter and contain only letters, digits, and underscores."
        )
    return str(prefix)

def _load_database_adapter_module(db_cfg: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """Load the database adapter module based on merged configuration."""
    try:
        cfg = db_cfg or _database_config()
        adapter_name = cfg.get("adapter")

        if not adapter_name:
            # Fallback or check packs?
            # Original code checked packs.
            # We can access full config via _CONFIG._full_config if needed, or add accessor.
            # But let's stick to 'adapter' key which should be set in defaults.yaml now.
            return None

        repo_dir = PathResolver.resolve_project_root()
        adapter_path = get_project_config_dir(repo_dir, create=False) / "packs" / str(adapter_name) / "db_adapter.py"
        if not adapter_path.exists():
            return None

        spec = _importlib_util.spec_from_file_location(
            f"edison_packs_{adapter_name}_db_adapter", adapter_path
        )
        if spec is None or spec.loader is None:
            return None

        module = _importlib_util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            return None
        return module
    except Exception:
        return None


def create_session_database(session_id: str) -> Optional[str]:
    """Create isolated sqldb database for session.

    Returns database URL if successful, otherwise None.
    """
    session_cfg = _session_config()
    config = session_cfg.get_worktree_config()
    db_config = session_cfg.get_database_config() or {}
    if not db_config.get("enabled", False):
        return None

    adapter_mod = _load_database_adapter_module(db_config)
    if adapter_mod is None or not hasattr(adapter_mod, "create_session_database"):
        return None

    db_prefix = _get_session_db_prefix(db_config)
    base_db_url = _get_database_url(db_config)
    repo_dir = PathResolver.resolve_project_root()

    try:
        return adapter_mod.create_session_database(
            session_id=session_id,
            db_prefix=db_prefix,
            base_db_url=base_db_url,
            repo_dir=repo_dir,
            worktree_config=config,
        )
    except Exception:
        return None


def drop_session_database(session_id: str) -> None:
    """Drop session database after merge/archive (best-effort)."""
    session_cfg = _session_config()
    db_config = session_cfg.get_database_config() or {}
    if not db_config.get("enabled", False):
        return
        
    adapter_mod = _load_database_adapter_module(db_config)
    if adapter_mod is None or not hasattr(adapter_mod, "drop_session_database"):
        return

    db_prefix = _get_session_db_prefix(db_config)
    base_db_url = _get_database_url(db_config)
    repo_dir = PathResolver.resolve_project_root()
    wt_config = session_cfg.get_worktree_config()

    try:
        adapter_mod.drop_session_database(
            session_id=session_id,
            db_prefix=db_prefix,
            base_db_url=base_db_url,
            repo_dir=repo_dir,
            worktree_config=wt_config,
        )
    except Exception:
        return
