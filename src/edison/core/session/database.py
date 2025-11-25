"""Database isolation and management."""
from __future__ import annotations

import os
import re
import importlib.util as _importlib_util
from typing import Any, Dict, Optional
from pathlib import Path

from ..paths.resolver import PathResolver
from .config import SessionConfig
from .worktree import _CONFIG as _WT_CONFIG # Reuse or new instance? Better new instance or passed in. 
# Actually worktree.py has _CONFIG = SessionConfig().
# Let's use our own instance.

_CONFIG = SessionConfig()

def _get_database_url() -> str:
    """Return DATABASE_URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL must be set in environment. No default provided for security reasons. "
            "Set: export DATABASE_URL='sqldb://user:pass@host:port/db'"
        )
    return str(url)

def _get_session_db_prefix() -> str:
    """Return the configured session DB prefix from project config."""
    db_cfg = _CONFIG.get_database_config()
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

def _load_database_adapter_module() -> Optional[Any]:
    """Load the database adapter module based on merged configuration."""
    try:
        db_cfg = _CONFIG.get_database_config()
        adapter_name = db_cfg.get("adapter")

        if not adapter_name:
            # Fallback or check packs?
            # Original code checked packs.
            # We can access full config via _CONFIG._full_config if needed, or add accessor.
            # But let's stick to 'adapter' key which should be set in defaults.yaml now.
            return None

        repo_dir = PathResolver.resolve_project_root()
        adapter_path = repo_dir / ".edison" / "packs" / str(adapter_name) / "db_adapter.py"
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
    config = _CONFIG.get_worktree_config()
    # Check database enabled flag? 
    # The original code checked 'enableDatabaseIsolation' in worktree config.
    # But defaults.yaml has 'database.enabled'.
    # Let's check both or prefer database config?
    # Original code: config.get("enableDatabaseIsolation", False) from worktree config.
    # Let's stick to that for now to match original logic, or switch to database.enabled?
    # The user wants "Configuration files".
    # defaults.yaml has `database: enabled: false`.
    # Let's check `_CONFIG.get_database_config().get("enabled")`.
    
    db_config = _CONFIG.get_database_config()
    if not db_config.get("enabled", False):
        return None

    adapter_mod = _load_database_adapter_module()
    if adapter_mod is None or not hasattr(adapter_mod, "create_session_database"):
        return None

    db_prefix = _get_session_db_prefix()
    base_db_url = _get_database_url()
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
    db_config = _CONFIG.get_database_config()
    if not db_config.get("enabled", False):
        return
        
    adapter_mod = _load_database_adapter_module()
    if adapter_mod is None or not hasattr(adapter_mod, "drop_session_database"):
        return

    db_prefix = _get_session_db_prefix()
    base_db_url = _get_database_url()
    repo_dir = PathResolver.resolve_project_root()
    wt_config = _CONFIG.get_worktree_config()

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
