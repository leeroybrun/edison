"""Managed-files platform adapter.

This adapter manages repository-level files that are not tied to a specific IDE
integration (e.g. `.gitignore`).

Behavior is config-driven and uses append-only, idempotent text updates (no
destructive edits).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.adapters.base import PlatformAdapter
from edison.core.utils.io import ensure_lines_present

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig


class ManagedFilesAdapterError(RuntimeError):
    """Error in managed-files adapter operations."""


class ManagedFilesAdapter(PlatformAdapter):
    """Platform adapter for managed repository files."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
    ) -> None:
        super().__init__(project_root=project_root, adapter_config=adapter_config)

    @property
    def platform_name(self) -> str:
        return "managed-files"

    def _iter_specs(self) -> List[Dict[str, Any]]:
        cfg = self.config.get("managed_files")
        if isinstance(cfg, dict) and isinstance(cfg.get("files"), list):
            return [s for s in (cfg.get("files") or []) if isinstance(s, dict)]

        return []

    def sync_all(self) -> Dict[str, List[Path]]:
        specs = self._iter_specs()
        if not specs:
            return {"files": []}

        written: List[Path] = []
        for spec in specs:
            raw_path = spec.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue

            path = Path(raw_path.strip())
            target = path if path.is_absolute() else (self.project_root / path)

            ensure_lines = spec.get("ensure_lines") or []
            if not isinstance(ensure_lines, list):
                continue
            required_lines = [str(line) for line in ensure_lines if str(line).strip() != ""]
            if not required_lines:
                continue

            create = bool(spec.get("create", True))
            ensure_blank_line_before = bool(spec.get("ensure_blank_line_before", True))
            ensure_trailing_newline = bool(spec.get("ensure_trailing_newline", True))

            changed = ensure_lines_present(
                target,
                required_lines,
                create=create,
                ensure_blank_line_before=ensure_blank_line_before,
                ensure_trailing_newline=ensure_trailing_newline,
            )
            if changed:
                written.append(target)

        return {"files": written}


__all__ = ["ManagedFilesAdapter", "ManagedFilesAdapterError"]
