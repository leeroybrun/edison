"""Root entry point generator (AGENTS.md).

Generates the root entry point file (AGENTS.md) that directs LLMs
to their appropriate role constitutions.

Uses the roots/AGENTS.md template with variable substitution:
- {{source_layers}}: List of composition sources
- {{timestamp}}: Current generation timestamp
- {{PROJECT_EDISON_DIR}}: Project config directory path
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from edison.data import get_data_path
from edison.core.config import ConfigManager
from edison.core.composition.core.paths import CompositionPathResolver
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.utils.io import ensure_directory
from ..utils.paths import resolve_project_dir_placeholders


def generate_root_entry(output_path: Path, repo_root: Optional[Path] = None) -> None:
    """Generate AGENTS.md root entry point from template.

    Uses the roots/AGENTS.md template and substitutes:
    - {{source_layers}}: List of composition sources
    - {{timestamp}}: Current generation timestamp
    - {{PROJECT_EDISON_DIR}}: Project config directory path

    Args:
        output_path: Path where the generated file should be written
        repo_root: Optional repository root path for testing
    """
    ensure_directory(output_path.parent)

    # Load template
    template_path = get_data_path("roots", "AGENTS.md")
    if not template_path.exists():
        raise FileNotFoundError(f"Root entry template not found at {template_path}")

    template = template_path.read_text(encoding="utf-8")

    # Use composition path resolver
    resolver = CompositionPathResolver(repo_root)
    project_dir = resolver.project_dir
    cfg_mgr = ConfigManager(repo_root=repo_root)

    # Build source layers info
    source_layers = "Core framework"
    config = cfg_mgr.load_config(validate=False)
    active_packs = (config.get("packs", {}) or {}).get("active", [])
    if active_packs:
        source_layers += f" + Packs ({', '.join(active_packs)})"

    # Substitute context variables
    content = template
    content = content.replace("{{source_layers}}", source_layers)
    content = content.replace("{{timestamp}}", datetime.now().isoformat())

    # Resolve {{PROJECT_EDISON_DIR}} placeholders
    content = resolve_project_dir_placeholders(
        content,
        project_dir=project_dir,
        target_path=output_path,
        repo_root=repo_root or resolver.project_root,
    )

    # Use CompositionFileWriter for consistent file output
    writer = CompositionFileWriter()
    writer.write_text(output_path, content)


# Backward-compatible alias
generate_canonical_entry = generate_root_entry


__all__ = [
    "generate_root_entry",
    "generate_canonical_entry",  # Backward-compatible alias
]
