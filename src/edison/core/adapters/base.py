"""Base class for platform adapters.

PlatformAdapter is the unified base for ALL platform integrations.
It merges the functionality of PromptAdapter and SyncAdapter into a single hierarchy.

Adapters handle:
- Platform-specific formatting and sync
- Reading from Edison _generated artifacts
- Writing to platform-specific layouts
- Configuration management
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from edison.core.composition.core.base import CompositionBase
from edison.core.utils.io import ensure_directory

from .components.base import AdapterContext
if TYPE_CHECKING:
    from edison.core.config.domains import AdaptersConfig
    from edison.core.composition.output.config import OutputConfigLoader


class PlatformAdapter(CompositionBase, ABC):
    """Unified base for ALL platform adapters.

    Inherits from CompositionBase to provide:
    - Unified path resolution (project_root, project_dir, core_dir, etc.)
    - Config management (cfg_mgr, config)
    - YAML utilities (load_yaml_safe, _load_layered_config)
    - Definition helpers (merge_definitions)
    - Lazy writer (writer property)

    Adds platform-specific:
    - platform_name property (identify the platform)
    - adapters_config property (adapter configurations)
    - output_config property (output path configuration)
    - sync_all() method (main sync entry point)
    - sync_agents_from_generated() helper (common agent sync pattern)

    Platform adapters integrate Edison's composition system with specific
    IDE/client configurations. They handle:
    - Configuration loading and validation
    - Syncing composed outputs to platform-specific formats
    - Platform-specific formatting (frontmatter, etc.)
    - Providing unified sync interfaces

    Subclasses must implement:
    - platform_name property: Unique identifier for the platform
    - sync_all(): Execute complete synchronization workflow

    Example:
        class MyPlatformAdapter(PlatformAdapter):
            @property
            def platform_name(self) -> str:
                return "my_platform"

            def sync_all(self) -> Dict[str, Any]:
                # Sync all components
                return {"synced": [...]}
    """

    # Lazy-loaded config objects
    _adapters_config: Optional["AdaptersConfig"] = None
    _output_config: Optional["OutputConfigLoader"] = None

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize the platform adapter.

        Args:
            project_root: Project root directory. If not provided, will be resolved
                         automatically using PathResolver.
        """
        # Initialize CompositionBase
        super().__init__(project_root=project_root)

        # Initialize lazy config loaders
        self._adapters_config = None
        self._output_config = None
        self._context: Optional[AdapterContext] = None

    @property
    def context(self) -> AdapterContext:
        """Shared adapter context for components."""
        if self._context is None:
            self._context = AdapterContext(
                project_root=self.project_root,
                project_dir=self.project_dir,
                core_dir=self.core_dir,
                bundled_packs_dir=self.bundled_packs_dir,
                project_packs_dir=self.project_packs_dir,
                cfg_mgr=self.cfg_mgr,
                config=self.config,
                writer=self.writer,
                adapter=self,
            )
        return self._context

    # =========================================================================
    # Abstract Properties and Methods
    # =========================================================================

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the unique identifier for this platform.

        Returns:
            Platform name (e.g., "claude", "cursor", "zen", "codex").
        """
        pass

    @abstractmethod
    def sync_all(self) -> Dict[str, Any]:
        """Execute complete synchronization workflow.

        This is the main entry point for syncing all Edison outputs to the
        target platform format. The exact behavior and return structure
        depends on the specific adapter implementation.

        Returns:
            Dictionary containing sync results. Structure varies by adapter
            but typically includes lists of paths for synced files.

        Example return values:
            - ClaudeAdapter: {"claude_md": [Path], "agents": [Path]}
            - CursorAdapter: {"cursorrules": [Path], "agents": [Path], "rules": [Path]}
            - ZenAdapter: {"roles": {role: [Path]}, "workflows": [Path]}
        """
        pass

    # =========================================================================
    # Config Properties
    # =========================================================================

    @property
    def adapters_config(self) -> "AdaptersConfig":
        """Lazy-load AdaptersConfig.

        Returns:
            AdaptersConfig instance for adapter-specific configurations.
        """
        if self._adapters_config is None:
            from edison.core.config.domains import AdaptersConfig

            self._adapters_config = AdaptersConfig(repo_root=self.project_root)
        return self._adapters_config

    @property
    def output_config(self) -> "OutputConfigLoader":
        """Lazy-load OutputConfigLoader.

        Returns:
            OutputConfigLoader instance for output path configuration.
        """
        if self._output_config is None:
            from edison.core.composition.output.config import OutputConfigLoader

            self._output_config = OutputConfigLoader(repo_root=self.project_root)
        return self._output_config

    # =========================================================================
    # Common Sync Utilities
    # =========================================================================

    def validate_structure(
        self,
        target_dir: Path,
        *,
        create_missing: bool = True,
    ) -> Path:
        """Ensure target directory structure exists.

        Args:
            target_dir: Directory to validate/create.
            create_missing: If True, create missing directories. Default: True.

        Returns:
            The target directory path.

        Raises:
            RuntimeError: If directory doesn't exist and create_missing=False.
        """
        if not target_dir.exists():
            if not create_missing:
                raise RuntimeError(f"Missing directory: {target_dir}")
            ensure_directory(target_dir)
        return target_dir

    def sync_agents_from_generated(
        self,
        target_dir: Path,
        *,
        add_frontmatter: bool = False,
        frontmatter_fn: Optional[Callable[[str, str], str]] = None,
    ) -> List[Path]:
        """Common pattern: sync _generated/agents/ to target directory.

        Args:
            target_dir: Destination directory for agent files.
            add_frontmatter: If True, use frontmatter_fn to add frontmatter.
            frontmatter_fn: Function(agent_name, content) -> content_with_frontmatter.

        Returns:
            List of created/updated file paths.
        """
        # Find generated agents directory
        generated_agents = self.project_dir / "_generated" / "agents"

        if not generated_agents.exists():
            return []

        # Ensure target exists
        self.validate_structure(target_dir)

        result: List[Path] = []

        for source_file in generated_agents.glob("*.md"):
            agent_name = source_file.stem
            content = source_file.read_text(encoding="utf-8")

            # Apply frontmatter if requested
            if add_frontmatter and frontmatter_fn:
                content = frontmatter_fn(agent_name, content)

            # Write to target
            target_file = target_dir / source_file.name
            self.writer.write_text(target_file, content)
            result.append(target_file)

        return result

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def create(cls, project_root: Optional[Path] = None) -> "PlatformAdapter":
        """Factory method for standard initialization.

        Args:
            project_root: Optional project root directory.

        Returns:
            Initialized platform adapter instance.
        """
        return cls(project_root=project_root)


__all__ = ["PlatformAdapter"]
