from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional


class PromptAdapter(ABC):
    """Base class for provider-specific prompt adapters.

    Adapters operate purely on Edison `_generated` artifacts and are
    responsible only for provider-specific formatting and filesystem
    layout. Composition (includes, pack overlays, DRY checks, etc.) is
    handled by the Edison engine before adapters run.
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
            except IndexError:  # pragma: no cover - defensive
                self.repo_root = Path.cwd().resolve()

    # ----- Abstract projection API -----
    @abstractmethod
    def render_orchestrator(self, guide_path: Path, manifest_path: Path) -> str:
        """Render orchestrator prompt from `_generated` sources."""

    @abstractmethod
    def render_agent(self, agent_name: str) -> str:
        """Render a single agent prompt from `_generated/agents/`."""

    @abstractmethod
    def render_validator(self, validator_name: str) -> str:
        """Render a single validator prompt from `_generated/validators/`."""

    @abstractmethod
    def write_outputs(self, output_root: Path) -> None:
        """Write all generated prompts to provider-specific location."""

    # ----- Shared helpers -----
    @property
    def agents_dir(self) -> Path:
        return self.generated_root / "agents"

    @property
    def validators_dir(self) -> Path:
        return self.generated_root / "validators"

    @property
    def orchestrator_guide_path(self) -> Path:
        return self.generated_root / "ORCHESTRATOR_GUIDE.md"

    @property
    def orchestrator_manifest_path(self) -> Path:
        return self.generated_root / "orchestrator-manifest.json"

    def list_agents(self) -> List[str]:
        if not self.agents_dir.exists():
            return []
        return sorted(p.stem for p in self.agents_dir.glob("*.md"))

    def list_validators(self) -> List[str]:
        if not self.validators_dir.exists():
            return []
        return sorted(p.stem for p in self.validators_dir.glob("*.md"))
