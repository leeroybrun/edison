"""Base class for IDE configuration composers.

Extends CompositionBase to provide unified path resolution, config management,
and YAML utilities for all IDE-specific composers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..core.base import CompositionBase
from ..output.writer import CompositionFileWriter
from edison.data import get_data_path


class IDEComposerBase(CompositionBase):
    """Base class providing shared initialization and utilities for IDE composers.

    Subclasses: HookComposer, CommandComposer, SettingsComposer

    Extends CompositionBase to provide:
    - Standardized repo_root and config loading
    - Shared path resolution (core_dir from bundled data, project_dir for overrides)
    - Canonical active_packs via PacksConfig
    - Common YAML/file loading patterns

    Architecture:
    - core_dir: ALWAYS bundled edison.data (no .edison/core/)
    - bundled_packs_dir: edison.data/packs/ for bundled packs
    - project_dir: .edison/ for project overrides
    - project_packs_dir: .edison/packs/ for project-level packs
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        repo_root: Optional[Path] = None,
    ) -> None:
        """Initialize composer with config and repo root.

        Args:
            config: Optional config dict to merge with loaded config.
            repo_root: Repository root path. Resolved automatically if not provided.
        """
        # Initialize CompositionBase
        super().__init__(project_root=repo_root, config=config)

        # Alias for backward compatibility
        self.repo_root = self.project_root

        # Initialize writer lazily
        self._writer: Optional[CompositionFileWriter] = None

    def _setup_composition_dirs(self) -> None:
        """Setup composition directories for IDE composers.

        IDE composers use bundled data directories:
        - core_dir: bundled edison.data
        - bundled_packs_dir: edison.data/packs/
        - project_dir: .edison/
        - project_packs_dir: .edison/packs/
        """
        # Core content is ALWAYS from bundled edison.data
        self.core_dir = Path(get_data_path(""))
        self.bundled_packs_dir = Path(get_data_path("packs"))

        # Project-level directories (project_dir set by CompositionBase)
        self.project_packs_dir = self.project_dir / "packs"

        # Alias for backward compatibility
        self.packs_dir = self.bundled_packs_dir

    @property
    def writer(self) -> CompositionFileWriter:
        """Get the composition file writer instance.

        Returns:
            CompositionFileWriter instance for writing files.
        """
        if self._writer is None:
            self._writer = CompositionFileWriter(base_dir=self.project_root)
        return self._writer

    # =========================================================================
    # IDE-Specific Utilities (kept for backward compatibility)
    # =========================================================================

    def _merge_definitions(
        self,
        merged: Dict[str, Dict[str, Any]],
        definitions: Any,
        key_getter: Callable[[Dict[str, Any]], Optional[str]] = lambda d: d.get("id"),
    ) -> Dict[str, Dict[str, Any]]:
        """Generic merge for YAML definitions by key.

        This method handles merging definitions from different sources
        (bundled core, packs, project) by extracting a unique key from each
        definition and deep-merging definitions with matching keys.

        Note: This is an alias for merge_definitions() from CompositionBase.

        Args:
            merged: Existing merged definitions dict (key -> definition)
            definitions: New definitions to merge (list or dict)
            key_getter: Function to extract the unique key from a definition dict.
                       Default extracts the "id" field.

        Returns:
            Updated merged definitions dict
        """
        return self.merge_definitions(merged, definitions, key_getter)


__all__ = ["IDEComposerBase"]
