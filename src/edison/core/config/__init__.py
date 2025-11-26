"""Edison configuration system.

This package provides centralized configuration management with domain-specific accessors.

Usage:
    from edison.core.config import ConfigManager
    from edison.core.config.domains import PacksConfig, SessionConfig

    # Direct config manager usage
    manager = ConfigManager(repo_root=Path("/path/to/project"))
    config = manager.load_config()

    # Domain-specific accessors (recommended)
    packs = PacksConfig(repo_root=Path("/path/to/project"))
    active = packs.active_packs

    # Cached config access
    from edison.core.config.cache import get_cached_config, clear_all_caches
    config = get_cached_config(repo_root)
"""
from __future__ import annotations

from .manager import ConfigManager
from .cache import get_cached_config, clear_all_caches, is_cached
from .base import BaseDomainConfig

# Re-export domain configs for convenience
from .domains import (
    PacksConfig,
    CompositionConfig,
    SessionConfig,
    QAConfig,
    OrchestratorConfig,
    ProjectConfig,
    TimeoutsConfig,
    WorkflowConfig,
    DatabaseConfig,
)

# Re-export workflow functions for convenience
from .domains.workflow import (
    load_workflow_config,
    get_task_states,
    get_qa_states,
    get_lifecycle_transition,
    get_timeout,
    get_semantic_state,
)

__all__ = [
    # Core
    "ConfigManager",
    "BaseDomainConfig",
    # Caching
    "get_cached_config",
    "clear_all_caches",
    "is_cached",
    # Domain configs
    "PacksConfig",
    "CompositionConfig",
    "SessionConfig",
    "QAConfig",
    "OrchestratorConfig",
    "ProjectConfig",
    "TimeoutsConfig",
    "WorkflowConfig",
    "DatabaseConfig",
    # Workflow functions
    "load_workflow_config",
    "get_task_states",
    "get_qa_states",
    "get_lifecycle_transition",
    "get_timeout",
    "get_semantic_state",
]
