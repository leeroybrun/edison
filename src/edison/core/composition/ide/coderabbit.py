#!/usr/bin/env python3
from __future__ import annotations

"""Compose CodeRabbit .coderabbit.yaml configuration."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.io import write_yaml, ensure_directory
from .base import IDEComposerBase


class CodeRabbitComposer(IDEComposerBase):
    """Build CodeRabbit configuration from Edison config."""

    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> None:
        super().__init__(config=config, repo_root=repo_root)
        self.project_config_dir = self.project_dir / "config"

    # ----- Loaders -----
    def load_core_coderabbit_config(self) -> Dict[str, Any]:
        """Load bundled CodeRabbit configuration from templates."""
        # Core template is in templates/configs/
        path = self.core_dir / "templates" / "configs" / "coderabbit.yaml"
        if not path.exists():
            path = self.core_dir / "templates" / "configs" / "coderabbit.yml"
        if path.exists():
            return self.cfg_mgr.load_yaml(path) or {}
        return {}

    def _load_pack_coderabbit_config(self, pack: str) -> Dict[str, Any]:
        """Load pack-level CodeRabbit configuration."""
        # Pack configs are in packs/{pack}/configs/
        path = self.packs_dir / pack / "configs" / "coderabbit.yaml"
        if not path.exists():
            path = self.packs_dir / pack / "configs" / "coderabbit.yml"
        if path.exists():
            return self.cfg_mgr.load_yaml(path) or {}
        return {}

    def _load_project_coderabbit_config(self) -> Dict[str, Any]:
        """Load project-level CodeRabbit configuration."""
        # Project configs are in .edison/configs/
        path = self.project_dir / "configs" / "coderabbit.yaml"
        if not path.exists():
            path = self.project_dir / "configs" / "coderabbit.yml"
        if path.exists():
            return self.cfg_mgr.load_yaml(path) or {}
        return {}

    # ----- Composition -----
    def _merge_with_list_append(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge with special handling for path_instructions (append lists).

        Args:
            base: Base configuration dict
            overlay: Overlay configuration dict

        Returns:
            Merged configuration with path_instructions appended
        """
        result = dict(base)

        for key, overlay_val in overlay.items():
            base_val = result.get(key)

            # Special handling for path_instructions - append lists
            if key == "path_instructions":
                if isinstance(base_val, list) and isinstance(overlay_val, list):
                    result[key] = base_val + overlay_val
                elif isinstance(overlay_val, list):
                    result[key] = overlay_val
            # Deep merge nested dicts
            elif isinstance(base_val, dict) and isinstance(overlay_val, dict):
                result[key] = self._merge_with_list_append(base_val, overlay_val)
            # Overlay takes precedence for other values
            else:
                result[key] = overlay_val

        return result

    def compose_coderabbit_config(self) -> Dict[str, Any]:
        """
        Compose CodeRabbit configuration from core, packs, and project layers.

        Returns:
            Dictionary ready to write to .coderabbit.yaml
        """
        # Start with core bundled config
        config = self.load_core_coderabbit_config()

        # Merge pack overlays with list appending for path_instructions
        for pack in self._active_packs():
            pack_config = self._load_pack_coderabbit_config(pack)
            config = self._merge_with_list_append(config, pack_config)

        # Merge project overrides
        project_config = self._load_project_coderabbit_config()
        config = self._merge_with_list_append(config, project_config)

        return config

    def _coderabbit_output_config(self) -> Dict[str, Any]:
        """Get CodeRabbit output configuration from composition config."""
        composition_config = self.config.get("composition", {})
        if isinstance(composition_config, dict):
            outputs = composition_config.get("outputs", {})
            if isinstance(outputs, dict):
                return outputs.get("coderabbit", {})
        return {}

    def write_coderabbit_config(self, output_path: Optional[Path] = None) -> Path:
        """
        Write CodeRabbit configuration file.

        Args:
            output_path: Optional custom output directory. If None, uses composition config.

        Returns:
            Path to written .coderabbit.yaml file
        """
        config = self.compose_coderabbit_config()

        # Determine output location
        if output_path:
            target = Path(output_path) / ".coderabbit.yaml"
        else:
            # Use composition.yaml output configuration
            output_config = self._coderabbit_output_config()
            if output_config.get("enabled", True):
                output_dir = output_config.get("output_path", ".")
                filename = output_config.get("filename", ".coderabbit.yaml")
                target = self.repo_root / output_dir / filename
            else:
                # Default to repo root
                target = self.repo_root / ".coderabbit.yaml"

        ensure_directory(target.parent)
        write_yaml(target, config)
        return target


def compose_coderabbit_config(
    repo_root: Optional[Path] = None,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Convenience function to compose CodeRabbit configuration.

    Args:
        repo_root: Repository root path
        config: Optional configuration override

    Returns:
        Composed CodeRabbit configuration dictionary
    """
    composer = CodeRabbitComposer(config=config, repo_root=repo_root)
    return composer.compose_coderabbit_config()


__all__ = ["CodeRabbitComposer", "compose_coderabbit_config"]
