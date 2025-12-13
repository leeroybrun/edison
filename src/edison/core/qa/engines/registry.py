"""Engine registry for the unified validator engine system.

This module provides the EngineRegistry class which:
- Loads engine configurations from validators.yaml
- Instantiates appropriate engine classes (CLIEngine, ZenMCPEngine)
- Handles fallback logic when primary engines are unavailable
- Delegates to ValidatorRegistry for roster building

NOTE: ValidatorRegistry is THE single source of truth for validator metadata.
This module only handles engine instantiation and execution.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import EngineConfig, ValidationResult
from .cli import CLIEngine
from .delegated import ZenMCPEngine

if TYPE_CHECKING:
    from edison.core.qa.evidence import EvidenceService
    from edison.core.registries.validators import ValidatorMetadata

logger = logging.getLogger(__name__)


class EngineRegistry:
    """Registry for validator engines with fallback support.

    The registry loads engine configurations, instantiates engine classes,
    and provides methods for running validators with automatic fallback
    when primary engines are unavailable.

    NOTE: For validator metadata, this class delegates to ValidatorRegistry.
    ValidatorRegistry is THE single source of truth for validator data.

    Example:
        registry = EngineRegistry(project_root=Path("/path/to/project"))

        # Run a specific validator
        result = registry.run_validator(
            validator_id="global-codex",
            task_id="T001",
            session_id="session-123",
            worktree_path=Path("/path/to/worktree"),
        )

        # For execution roster building, use ValidatorRegistry directly:
        from edison.core.registries.validators import ValidatorRegistry
        validator_registry = ValidatorRegistry()
        roster = validator_registry.build_execution_roster(
            task_id="T001",
            session_id="session-123",
            wave="critical",
        )
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the engine registry.

        Args:
            project_root: Project root path for configuration loading
        """
        from edison.core.config.domains.qa import QAConfig
        from edison.core.registries.validators import ValidatorRegistry

        self.project_root = project_root
        self._qa_config = QAConfig(repo_root=project_root)
        self._validator_registry = ValidatorRegistry(project_root=project_root)
        self._engines: dict[str, CLIEngine | ZenMCPEngine] = {}
        self._engine_configs: dict[str, EngineConfig] = {}

        # Load engine configurations only (validators come from ValidatorRegistry)
        self._load_engine_configurations()

    def _load_engine_configurations(self) -> None:
        """Load engine configurations from QAConfig."""
        validation_config = self._qa_config.validation_config

        # Load engine configurations only
        engines = validation_config.get("engines", {})
        if isinstance(engines, dict):
            for engine_id, engine_data in engines.items():
                if isinstance(engine_data, dict):
                    self._engine_configs[engine_id] = EngineConfig.from_dict(
                        engine_id, engine_data
                    )

        logger.debug(f"Loaded {len(self._engine_configs)} engines")

    def _get_or_create_engine(self, engine_id: str) -> CLIEngine | ZenMCPEngine | None:
        """Get or create an engine instance.

        Args:
            engine_id: Engine identifier

        Returns:
            Engine instance or None if not found
        """
        if engine_id in self._engines:
            return self._engines[engine_id]

        engine_config = self._engine_configs.get(engine_id)
        if not engine_config:
            # Try to create a default config for known engines
            engine_config = self._create_default_engine_config(engine_id)

        if not engine_config:
            logger.warning(f"Engine '{engine_id}' not found in configuration")
            return None

        # Instantiate appropriate engine class
        if engine_config.type == "delegated":
            engine = ZenMCPEngine(engine_config, self.project_root)
        else:
            engine = CLIEngine(engine_config, self.project_root)

        self._engines[engine_id] = engine
        return engine

    def _create_default_engine_config(self, engine_id: str) -> EngineConfig | None:
        """Create default engine config for known engines.

        Args:
            engine_id: Engine identifier

        Returns:
            Default EngineConfig or None
        """
        defaults = {
            "codex-cli": {
                "type": "cli",
                "command": "codex",
                "subcommand": "exec",
                "output_flags": [],
                "read_only_flags": [],
                "response_parser": "codex",
            },
            "claude-cli": {
                "type": "cli",
                "command": "claude",
                "subcommand": "-p",
                "output_flags": ["--output-format", "json"],
                "read_only_flags": ["--permission-mode", "plan"],
                "response_parser": "claude",
            },
            "gemini-cli": {
                "type": "cli",
                "command": "gemini",
                "subcommand": "-p",
                "output_flags": ["--output-format", "json"],
                "read_only_flags": [],
                "response_parser": "gemini",
            },
            "auggie-cli": {
                "type": "cli",
                "command": "auggie",
                "subcommand": "",
                "output_flags": ["--output-format", "json"],
                "read_only_flags": ["--print", "--quiet"],
                "response_parser": "auggie",
            },
            "coderabbit-cli": {
                "type": "cli",
                "command": "coderabbit",
                "subcommand": "review",
                "output_flags": [],
                "read_only_flags": ["--prompt-only"],
                "response_parser": "coderabbit",
            },
            "zen-mcp": {
                "type": "delegated",
                "command": "",
                "response_parser": "plain_text",
                "description": "Generate delegation instructions for orchestrator",
            },
        }

        if engine_id in defaults:
            return EngineConfig.from_dict(engine_id, defaults[engine_id])
        return None

    def get_validator(self, validator_id: str) -> "ValidatorMetadata | None":
        """Get validator configuration by ID.

        Delegates to ValidatorRegistry for single source of truth.

        Args:
            validator_id: Validator identifier

        Returns:
            ValidatorMetadata or None if not found
        """
        return self._validator_registry.get(validator_id)

    def list_validators(self) -> list[str]:
        """List all registered validator IDs.

        Delegates to ValidatorRegistry for single source of truth.

        Returns:
            List of validator identifiers
        """
        return self._validator_registry.list_names()

    # NOTE: get_validators_for_wave() has been removed.
    # Use ValidatorRegistry.get_by_wave() directly as the single source of truth.

    def run_validator(
        self,
        validator_id: str,
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None = None,
        evidence_service: "EvidenceService | None" = None,
    ) -> ValidationResult:
        """Run a specific validator by ID.

        Handles engine selection and fallback logic automatically.

        Args:
            validator_id: Validator identifier
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Path to git worktree
            round_num: Optional validation round number
            evidence_service: Optional evidence service

        Returns:
            ValidationResult from the validator

        Raises:
            ValueError: If validator not found
        """
        validator = self.get_validator(validator_id)
        if not validator:
            raise ValueError(f"Validator '{validator_id}' not found")

        # Get primary engine
        engine = self._get_or_create_engine(validator.engine)

        # Check if primary engine can execute
        if engine and engine.can_execute():
            logger.info(f"Running validator '{validator_id}' with engine '{validator.engine}'")
            return engine.run(
                validator=validator,
                task_id=task_id,
                session_id=session_id,
                worktree_path=worktree_path,
                round_num=round_num,
                evidence_service=evidence_service,
            )

        # Try fallback engine
        if validator.fallback_engine:
            fallback = self._get_or_create_engine(validator.fallback_engine)
            if fallback and fallback.can_execute():
                logger.info(
                    f"Primary engine '{validator.engine}' unavailable, "
                    f"using fallback '{validator.fallback_engine}' for '{validator_id}'"
                )
                return fallback.run(
                    validator=validator,
                    task_id=task_id,
                    session_id=session_id,
                    worktree_path=worktree_path,
                    round_num=round_num,
                    evidence_service=evidence_service,
                )

        # No engine available
        logger.error(f"No available engine for validator '{validator_id}'")
        return ValidationResult(
            validator_id=validator_id,
            verdict="blocked",
            summary=f"No available engine for validator. Primary: {validator.engine}, Fallback: {validator.fallback_engine}",
            error="Engine not available",
        )

    # NOTE: build_execution_roster() has been removed.
    # Use ValidatorRegistry.build_execution_roster() directly as the single source of truth.
    # Access via: self._validator_registry.build_execution_roster(...)


__all__ = ["EngineRegistry"]

