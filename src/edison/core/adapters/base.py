"""Base class for provider-specific prompt adapters.

Adapters operate purely on Edison `_generated` artifacts and are
responsible only for provider-specific formatting and filesystem
layout. Composition (includes, pack overlays, DRY checks, etc.) is
handled by the Edison engine before adapters run.

Uses ConfigMixin for unified config loading.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._config import ConfigMixin


class PromptAdapter(ConfigMixin, ABC):
    """Base class for provider-specific prompt adapters.

    Inherits from ConfigMixin to provide unified config loading with caching.

    The unified composition engine produces:
    - _generated/agents/*.md - Agent prompts
    - _generated/validators/*.md - Validator prompts
    - _generated/constitutions/*.md - Role constitutions
    - _generated/clients/*.md - Client-specific files (claude.md, zen.md)
    - _generated/guidelines/*.md - Composed guidelines
    """

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        """Initialize adapter with generated root and repo root.

        Args:
            generated_root: Path to _generated directory.
            repo_root: Optional repository root. If not provided, will be inferred.
        """
        self.generated_root: Path = generated_root.resolve()

        # Best-effort repo root inference when not provided explicitly.
        if repo_root is not None:
            self.repo_root = repo_root.resolve()
        else:
            # Typical layout: <repo>/<project_config_dir>/_generated
            try:
                self.repo_root = self.generated_root.parents[1]
            except IndexError:
                self.repo_root = Path.cwd().resolve()

        # Initialize ConfigMixin's cache
        self._cached_config: Optional[Dict[str, Any]] = None

    # ----- Default API -----
    def render_agent(self, agent_name: str) -> str:
        """Render a single agent prompt from `_generated/agents/`.

        Default implementation reads the agent file and applies post-processing.
        Override _post_process_agent() to customize formatting instead of this method.

        Args:
            agent_name: Name of the agent to render.

        Returns:
            Rendered agent content.

        Raises:
            FileNotFoundError: If agent file does not exist.
        """
        source = self.agents_dir / f"{agent_name}.md"
        if not source.exists():
            raise FileNotFoundError(f"Agent not found: {source}")
        content = source.read_text(encoding="utf-8")
        return self._post_process_agent(agent_name, content)

    def render_validator(self, validator_name: str) -> str:
        """Render a single validator prompt from `_generated/validators/`.

        Default implementation reads the validator file and applies post-processing.
        Override _post_process_validator() to customize formatting instead of this method.

        Args:
            validator_name: Name of the validator to render.

        Returns:
            Rendered validator content.

        Raises:
            FileNotFoundError: If validator file does not exist.
        """
        source = self.validators_dir / f"{validator_name}.md"
        if not source.exists():
            raise FileNotFoundError(f"Validator not found: {source}")
        content = source.read_text(encoding="utf-8")
        return self._post_process_validator(validator_name, content)

    def render_client(self, client_name: str) -> str:
        """Render a client file from `_generated/clients/`.

        Args:
            client_name: Name of the client (e.g., 'claude', 'zen').

        Returns:
            Client file content.

        Raises:
            FileNotFoundError: If client file does not exist.
        """
        source = self.clients_dir / f"{client_name}.md"
        if not source.exists():
            raise FileNotFoundError(f"Client file not found: {source}")
        return source.read_text(encoding="utf-8")

    @abstractmethod
    def write_outputs(self, output_root: Path) -> None:
        """Write all generated prompts to provider-specific location."""

    # ----- Extension Hooks -----
    def _post_process_agent(self, agent_name: str, content: str) -> str:
        """Hook for subclasses to format agent content.

        Override this method to add provider-specific formatting to agents.
        Default implementation returns content unchanged.

        Args:
            agent_name: Name of the agent.
            content: Raw agent content from file.

        Returns:
            Formatted agent content.
        """
        return content

    def _post_process_validator(self, validator_name: str, content: str) -> str:
        """Hook for subclasses to format validator content.

        Override this method to add provider-specific formatting to validators.
        Default implementation returns content unchanged.

        Args:
            validator_name: Name of the validator.
            content: Raw validator content from file.

        Returns:
            Formatted validator content.
        """
        return content

    # ----- Shared path helpers -----
    @property
    def agents_dir(self) -> Path:
        """Path to _generated/agents/."""
        return self.generated_root / "agents"

    @property
    def validators_dir(self) -> Path:
        """Path to _generated/validators/."""
        return self.generated_root / "validators"

    @property
    def constitutions_dir(self) -> Path:
        """Path to _generated/constitutions/."""
        return self.generated_root / "constitutions"

    @property
    def clients_dir(self) -> Path:
        """Path to _generated/clients/."""
        return self.generated_root / "clients"

    @property
    def guidelines_dir(self) -> Path:
        """Path to _generated/guidelines/."""
        return self.generated_root / "guidelines"

    # ----- Constitution paths -----
    @property
    def orchestrator_constitution_path(self) -> Path:
        """Path to orchestrator constitution (replaces ORCHESTRATOR_GUIDE.md)."""
        return self.constitutions_dir / "ORCHESTRATORS.md"

    @property
    def agent_constitution_path(self) -> Path:
        """Path to agent constitution."""
        return self.constitutions_dir / "AGENTS.md"

    @property
    def validator_constitution_path(self) -> Path:
        """Path to validator constitution."""
        return self.constitutions_dir / "VALIDATORS.md"

    # ----- List helpers -----
    def list_agents(self) -> List[str]:
        """List all agent names from _generated/agents/."""
        if not self.agents_dir.exists():
            return []
        return sorted(p.stem for p in self.agents_dir.glob("*.md"))

    def list_validators(self) -> List[str]:
        """List all validator names from _generated/validators/."""
        if not self.validators_dir.exists():
            return []
        return sorted(p.stem for p in self.validators_dir.glob("*.md"))

    def list_clients(self) -> List[str]:
        """List all client names from _generated/clients/."""
        if not self.clients_dir.exists():
            return []
        return sorted(p.stem for p in self.clients_dir.glob("*.md"))
