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
    from edison.core.config.domains.composition import AdapterConfig, CompositionConfig


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
    - adapter_config property (adapter-specific configuration from loader)
    - composition_config property (unified CompositionConfig access)
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

    # Adapter configuration from loader
    _adapter_config: Optional["AdapterConfig"] = None
    _composition_config: Optional["CompositionConfig"] = None

    def __init__(
        self,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
    ) -> None:
        """Initialize the platform adapter.

        Args:
            project_root: Project root directory. If not provided, will be resolved
                         automatically using PathResolver.
            adapter_config: Adapter configuration from AdapterLoader. If not provided,
                           will be loaded from CompositionConfig using platform_name.
        """
        # Initialize CompositionBase
        super().__init__(project_root=project_root)

        # Store adapter config from loader
        self._adapter_config = adapter_config
        self._composition_config = None
        self._context: Optional[AdapterContext] = None

    @property
    def composition_config(self) -> "CompositionConfig":
        """Get CompositionConfig instance.
        
        Returns:
            CompositionConfig for accessing unified configuration.
        """
        if self._composition_config is None:
            from edison.core.config.domains.composition import CompositionConfig
            self._composition_config = CompositionConfig(repo_root=self.project_root)
        return self._composition_config

    @property
    def adapter_config(self) -> Optional["AdapterConfig"]:
        """Get adapter-specific configuration.
        
        Returns configuration passed from AdapterLoader, or looks it up
        from CompositionConfig using platform_name.
        
        Returns:
            AdapterConfig or None if not found.
        """
        if self._adapter_config is None:
            # Try to load from CompositionConfig using platform_name
            self._adapter_config = self.composition_config.get_adapter(self.platform_name)
        return self._adapter_config

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
    # Config Access Helpers
    # =========================================================================

    def get_output_path(self) -> Path:
        """Get the output path for this adapter.
        
        Returns:
            Resolved output directory path.
        """
        if self.adapter_config and self.adapter_config.output_path:
            return self.composition_config.resolve_output_path(
                self.adapter_config.output_path
            )
        # Fallback to platform-specific default
        return self.project_root / f".{self.platform_name}"

    def get_sync_config(self, sync_name: str) -> Optional[Any]:
        """Get sync configuration by name.
        
        Args:
            sync_name: Name of the sync config (e.g., "agents", "prompts")
            
        Returns:
            AdapterSyncConfig or None if not found.
        """
        if self.adapter_config and self.adapter_config.sync:
            return self.adapter_config.sync.get(sync_name)
        return None

    def is_sync_enabled(self, sync_name: str) -> bool:
        """Check if a sync is enabled.
        
        Args:
            sync_name: Name of the sync config
            
        Returns:
            True if sync is enabled, False otherwise.
        """
        sync_cfg = self.get_sync_config(sync_name)
        return sync_cfg is not None and sync_cfg.enabled

    def get_sync_destination(self, sync_name: str) -> Optional[Path]:
        """Get resolved sync destination path.
        
        Args:
            sync_name: Name of the sync config
            
        Returns:
            Resolved destination path or None if not configured.
        """
        sync_cfg = self.get_sync_config(sync_name)
        if sync_cfg and sync_cfg.destination:
            return self.composition_config.resolve_output_path(sync_cfg.destination)
        return None

    def get_sync_source(self, sync_name: str) -> Optional[Path]:
        """Get resolved sync source path.
        
        Args:
            sync_name: Name of the sync config
            
        Returns:
            Resolved source path or None if not configured.
        """
        sync_cfg = self.get_sync_config(sync_name)
        if sync_cfg and sync_cfg.source:
            return self.composition_config.resolve_output_path(sync_cfg.source)
        return None

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
        filename_pattern: str = "{name}.md",
    ) -> List[Path]:
        """Common pattern: sync _generated/agents/ to target directory.

        Args:
            target_dir: Destination directory for agent files.
            add_frontmatter: If True, use frontmatter_fn to add frontmatter.
            frontmatter_fn: Function(agent_name, content) -> content_with_frontmatter.
            filename_pattern: Pattern for output filenames.

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

        for source_file in sorted(generated_agents.glob("*.md")):
            agent_name = source_file.stem
            content = source_file.read_text(encoding="utf-8")

            # Apply frontmatter if requested
            if add_frontmatter and frontmatter_fn:
                content = frontmatter_fn(agent_name, content)

            # Write to target with configured filename pattern
            filename = filename_pattern.format(name=agent_name)
            target_file = target_dir / filename
            self.write_text_managed(target_file, content)
            result.append(target_file)

        return result

    def sync_from_config(self, sync_name: str) -> List[Path]:
        """Sync files based on configuration.
        
        Uses sync configuration to copy files from source to destination.
        
        Args:
            sync_name: Name of the sync config (e.g., "agents", "prompts")
            
        Returns:
            List of created/updated file paths.
        """
        sync_cfg = self.get_sync_config(sync_name)
        if not sync_cfg or not sync_cfg.enabled:
            return []
        
        source_dir = self.get_sync_source(sync_name)
        dest_dir = self.get_sync_destination(sync_name)
        
        if not source_dir or not dest_dir or not source_dir.exists():
            return []
        
        self.validate_structure(dest_dir)
        
        pattern = getattr(sync_cfg, "source_glob", "*.md") or "*.md"
        recursive = bool(getattr(sync_cfg, "recursive", False))

        candidates = source_dir.rglob(pattern) if recursive else source_dir.glob(pattern)

        result: List[Path] = []
        for source_file in sorted([p for p in candidates if p.is_file()]):
            name = source_file.stem
            content = source_file.read_text(encoding="utf-8")

            filename = sync_cfg.filename_pattern.format(name=name)
            target_file = dest_dir / filename
            self.write_text_managed(target_file, content)
            result.append(target_file)
        
        return result

    # =========================================================================
    # Managed Writes
    # =========================================================================

    def write_text_managed(self, path: Path, content: str) -> Path:
        """Write a file applying any configured write policies for this adapter."""
        policy = self.composition_config.resolve_write_policy(
            path=path,
            adapter=self.platform_name,
        )
        return self.writer.write_text_with_policy(path, content, policy=policy)

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def create(
        cls,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
    ) -> "PlatformAdapter":
        """Factory method for standard initialization.

        Args:
            project_root: Optional project root directory.
            adapter_config: Optional adapter configuration.

        Returns:
            Initialized platform adapter instance.
        """
        return cls(project_root=project_root, adapter_config=adapter_config)


__all__ = ["PlatformAdapter"]
