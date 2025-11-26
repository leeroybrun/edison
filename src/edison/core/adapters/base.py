from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class PromptAdapter(ABC):
    """Base class for provider-specific prompt adapters.

    Adapters operate purely on Edison `_generated` artifacts and are
    responsible only for provider-specific formatting and filesystem
    layout. Composition (includes, pack overlays, DRY checks, etc.) is
    handled by the Edison engine before adapters run.
    
    The unified composition engine produces:
    - _generated/agents/*.md - Agent prompts
    - _generated/validators/*.md - Validator prompts
    - _generated/constitutions/*.md - Role constitutions
    - _generated/clients/*.md - Client-specific files (claude.md, zen.md)
    - _generated/guidelines/*.md - Composed guidelines
    """

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
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

    # ----- Abstract API -----
    @abstractmethod
    def render_agent(self, agent_name: str) -> str:
        """Render a single agent prompt from `_generated/agents/`."""

    @abstractmethod
    def render_validator(self, validator_name: str) -> str:
        """Render a single validator prompt from `_generated/validators/`."""

    @abstractmethod
    def write_outputs(self, output_root: Path) -> None:
        """Write all generated prompts to provider-specific location."""

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
