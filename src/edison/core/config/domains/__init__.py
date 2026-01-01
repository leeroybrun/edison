"""Domain-specific configuration accessors.

This package contains all domain-specific config classes that extend BaseDomainConfig.
Each domain config provides typed, cached access to a specific section of Edison configuration.

Available domain configs:
- PacksConfig: Pack activation and management
- CompositionConfig: Content composition settings (unified config for content types and adapters)
- SessionConfig: Session management and state machine
- QAConfig: QA and validation settings
- TaskConfig: Task management and state machine
- OrchestratorConfig: Orchestrator profiles
- ProjectConfig: Project metadata (name, owner, audit terms)
- TimeoutsConfig: Operation timeouts
- WorkflowConfig: Workflow lifecycle configuration
- DatabaseConfig: Database connection and isolation
- ProcessConfig: Process detection patterns for session ID inference
- CLIConfig: CLI output formatting and display settings
- JSONIOConfig: JSON I/O formatting and encoding settings
- Context7Config: Context7 package detection and aliases

Note: AdaptersConfig has been removed. Use CompositionConfig.adapters instead.

Usage:
    from edison.core.config.domains import PacksConfig, SessionConfig, TaskConfig

    packs = PacksConfig(repo_root=Path("/path/to/project"))
    active = packs.active_packs

    session = SessionConfig(repo_root=Path("/path/to/project"))
    states = session.get_states("task")

    task = TaskConfig(repo_root=Path("/path/to/project"))
    task_states = task.task_states()
    
    # For adapter configuration:
    comp = CompositionConfig(repo_root=Path("/path/to/project"))
    for adapter in comp.get_enabled_adapters():
        print(adapter.name, adapter.adapter_class)
"""
from __future__ import annotations

from .packs import PacksConfig
from .composition import (
    CompositionConfig,
    ContentTypeConfig,
    AdapterConfig,
    AdapterSyncConfig,
)
from .session import SessionConfig
from .qa import QAConfig
from .task import TaskConfig
from .orchestrator import OrchestratorConfig
from .project import ProjectConfig
from .timeouts import TimeoutsConfig
from .workflow import WorkflowConfig
from .database import DatabaseConfig
from .process import ProcessConfig
from .cli import CLIConfig
from .json_io import JSONIOConfig
from .context7 import Context7Config
from .logging import LoggingConfig
from .tdd import TDDConfig

__all__: list[str] = [
    "PacksConfig",
    "CompositionConfig",
    "ContentTypeConfig",
    "AdapterConfig",
    "AdapterSyncConfig",
    "SessionConfig",
    "QAConfig",
    "TaskConfig",
    "OrchestratorConfig",
    "ProjectConfig",
    "TimeoutsConfig",
    "WorkflowConfig",
    "DatabaseConfig",
    "ProcessConfig",
    "CLIConfig",
    "JSONIOConfig",
    "Context7Config",
    "LoggingConfig",
    "TDDConfig",
]
