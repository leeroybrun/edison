"""Cache utilities for test isolation.

This module provides utilities for resetting Edison caches between tests
to ensure proper isolation.
"""
from __future__ import annotations


def reset_edison_caches() -> None:
    """Reset ALL global caches in Edison modules to ensure test isolation.

    This is a centralized function to clear all module-level caches that
    might persist state between tests.
    """
    # Path resolver cache
    try:
        import edison.core.utils.paths.resolver as paths
        paths._PROJECT_ROOT_CACHE = None
    except Exception:
        pass

    # Task paths caches
    try:
        import edison.core.task.paths as task_paths
        task_paths._ROOT_CACHE = None
        task_paths._SESSION_CONFIG_CACHE = None
        task_paths._TASK_CONFIG_CACHE = None
        task_paths._TASK_ROOT_CACHE = None
        task_paths._QA_ROOT_CACHE = None
        task_paths._SESSIONS_ROOT_CACHE = None
        task_paths._TASK_DIRS_CACHE = None
        task_paths._QA_DIRS_CACHE = None
        task_paths._SESSION_DIRS_CACHE = None
        task_paths._PREFIX_CACHE = None
    except Exception:
        pass

    # Clear ALL config caches (central cache.py)
    try:
        from edison.core.config.cache import clear_all_caches
        clear_all_caches()
    except Exception:
        pass

    # Session config cache (centralized in _config.py)
    try:
        from edison.core.session._config import reset_config_cache
        reset_config_cache()
    except Exception:
        pass

    # Composition module caches
    composition_modules = [
        "edison.core.composition.includes",
        "edison.core.composition.commands",
        "edison.core.composition.composers",
        "edison.core.composition.settings",
        "edison.core.composition.hooks",
    ]
    for mod_name in composition_modules:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            if hasattr(mod, '_REPO_ROOT_OVERRIDE'):
                mod._REPO_ROOT_OVERRIDE = None
        except Exception:
            pass

    # ConfigManager cache
    try:
        import edison.core.config as config_mod
        if hasattr(config_mod, '_CONFIG_CACHE'):
            config_mod._CONFIG_CACHE = {}
    except Exception:
        pass

    # Project config cache
    try:
        from edison.core.utils import project_config
        project_config.reset_project_config_cache()
    except Exception:
        pass

    # Management paths singleton cache
    try:
        import edison.core.utils.paths.management as management
        management._paths_instance = None
    except Exception:
        pass
