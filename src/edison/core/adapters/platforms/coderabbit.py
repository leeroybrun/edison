"""CodeRabbit platform adapter.

Handles:
- Composing .coderabbit.yaml configuration from Edison layers
- Merging core, pack, and project configurations
- Special handling for path_instructions (list appending via ["+", ...] syntax)

Note: CodeRabbit config is platform-specific (templates/config/coderabbit.yaml),
separate from Edison's main config system. Uses ConfigManager for path resolution
but has specialized loading for platform-specific config files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.adapters.base import PlatformAdapter
from edison.core.utils.merge import deep_merge

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig


class CoderabbitAdapterError(RuntimeError):
    """Error in CodeRabbit adapter operations."""


class CoderabbitAdapter(PlatformAdapter):
    """Platform adapter for CodeRabbit.

    This adapter:
    - Composes CodeRabbit configuration from core, packs, and project layers
    - Writes to .coderabbit.yaml file
    - Uses ConfigManager for path resolution
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
    ) -> None:
        """Initialize CodeRabbit adapter.

        Args:
            project_root: Project root directory.
            adapter_config: Adapter configuration from loader.
        """
        super().__init__(project_root=project_root, adapter_config=adapter_config)
        self.project_config_dir = self.project_dir

    # =========================================================================
    # Platform Properties
    # =========================================================================

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "coderabbit"

    @property
    def output_filename(self) -> str:
        """Get output filename from config."""
        if self.adapter_config and self.adapter_config.filename:
            return self.adapter_config.filename
        return ".coderabbit.yaml"

    # =========================================================================
    # Config Loading (platform-specific coderabbit.yaml files)
    # =========================================================================

    def _load_coderabbit_yaml(self, path: Path) -> Dict[str, Any]:
        """Load CodeRabbit YAML with extension fallback."""
        if not path.exists():
            # Try alternate extension
            alt = path.with_suffix(".yml" if path.suffix == ".yaml" else ".yaml")
            if alt.exists():
                path = alt
            else:
                return {}
        return self.cfg_mgr.load_yaml(path) or {}

    def compose_coderabbit_config(self) -> Dict[str, Any]:
        """Compose CodeRabbit configuration from core, packs, and project layers.

        Uses ConfigManager's deep_merge with ["+", ...] syntax for array appending.
        For path_instructions, use ["+", instruction1, instruction2] in YAML.

        Returns:
            Dictionary ready to write to .coderabbit.yaml
        """
        config: Dict[str, Any] = {}

        # Layer 1: Core bundled config (templates/config/)
        core_path = self.core_dir / "templates" / "config" / "coderabbit.yaml"
        config = deep_merge(config, self._load_coderabbit_yaml(core_path))

        # Layer 2: Pack configs (bundled + project packs)
        for pack in self.get_active_packs():
            # Bundled pack
            bundled_path = self.bundled_packs_dir / pack / "config" / "coderabbit.yaml"
            config = deep_merge(config, self._load_coderabbit_yaml(bundled_path))
            # Project pack override
            project_pack_path = self.project_packs_dir / pack / "config" / "coderabbit.yaml"
            config = deep_merge(config, self._load_coderabbit_yaml(project_pack_path))

        # Layer 3: Project config
        project_path = self.project_dir / "config" / "coderabbit.yaml"
        config = deep_merge(config, self._load_coderabbit_yaml(project_path))

        return config

    def write_coderabbit_config(self, output_path: Optional[Path] = None) -> Path:
        """Write CodeRabbit configuration file.

        Args:
            output_path: Optional custom output directory. If None, uses composition config.

        Returns:
            Path to written .coderabbit.yaml file
        """
        config = self.compose_coderabbit_config()

        # Determine output location
        if output_path:
            target = Path(output_path) / self.output_filename
        else:
            # Use adapter config from CompositionConfig
            output_dir = self.get_output_path()
            target = output_dir / self.output_filename

        written_path = self.writer.write_yaml(target, config)
        return written_path

    # =========================================================================
    # Sync Methods
    # =========================================================================

    def sync_all(self) -> Dict[str, List[Path]]:
        """Execute complete synchronization workflow.

        Syncs:
        - .coderabbit.yaml configuration file

        Returns:
            Dictionary containing sync results with keys:
            - config: List with .coderabbit.yaml path
        """
        result: Dict[str, List[Path]] = {
            "config": [],
        }

        config_path = self.write_coderabbit_config()
        result["config"].append(config_path)

        return result


__all__ = ["CoderabbitAdapter", "CoderabbitAdapterError"]
