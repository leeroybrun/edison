"""Domain-specific configuration accessors.

This package contains all domain-specific config classes that extend BaseDomainConfig.
Each domain config provides typed, cached access to a specific section of Edison configuration.

Available domain configs:
- PacksConfig: Pack activation and management
- CompositionConfig: Content composition settings
- SessionConfig: Session management and state machine
- QAConfig: QA and validation settings
- OrchestratorConfig: Orchestrator profiles
- ProjectConfig: Project metadata (name, owner, audit terms)
- TimeoutsConfig: Operation timeouts
- WorkflowConfig: Workflow lifecycle configuration
- DatabaseConfig: Database connection and isolation

Usage:
    from edison.core.config.domains import PacksConfig, SessionConfig

    packs = PacksConfig(repo_root=Path("/path/to/project"))
    active = packs.active_packs

    session = SessionConfig(repo_root=Path("/path/to/project"))
    states = session.get_states("task")
"""
from __future__ import annotations

from .packs import PacksConfig
from .composition import CompositionConfig
from .session import SessionConfig
from .qa import QAConfig
from .orchestrator import OrchestratorConfig
from .project import ProjectConfig
from .timeouts import TimeoutsConfig
from .workflow import WorkflowConfig
from .database import DatabaseConfig

__all__: list[str] = [
    "PacksConfig",
    "CompositionConfig",
    "SessionConfig",
    "QAConfig",
    "OrchestratorConfig",
    "ProjectConfig",
    "TimeoutsConfig",
    "WorkflowConfig",
    "DatabaseConfig",
]



