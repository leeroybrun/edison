from __future__ import annotations

"""Formatting utilities for composed content."""

import re
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

from edison.core.utils.text import render_conditional_includes

if TYPE_CHECKING:
    from edison.core.composition.core import CompositionPathResolver


def format_for_zen(content: str) -> str:
    """Format composed content for Zen MCP consumption (plain text)."""
    txt = content.replace("```python", "").replace("```typescript", "").replace("```", "")
    txt = re.sub(r"^### (.+)$", r"**\1**", txt, flags=re.MULTILINE)
    txt = re.sub(r"^## (.+)$", r"\n**\1**\n", txt, flags=re.MULTILINE)
    txt = re.sub(r"^# (.+)$", r"\n=== \1 ===\n", txt, flags=re.MULTILINE)
    return txt


def format_rules_context(rules_config: Dict) -> str:
    """Render rules configuration into human-readable Markdown."""
    lines: List[str] = []
    lines.append("## State-Based Rules")

    for state, rules in (rules_config.get("byState", {}) or {}).items():
        lines.append(f"\n**{str(state).upper()}**:")
        for rule in rules or []:
            blocking = "🔴 BLOCKING" if rule.get("blocking") else "⚠️  WARNING"
            desc = rule.get("description", "")
            lines.append(f"  - [{blocking}] {desc}")
            if rule.get("reference"):
                lines.append(f"    Reference: {rule['reference']}")

    lines.append("\n## Task-Type Rules")
    for task_type, rules in (rules_config.get("byTaskType", {}) or {}).items():
        lines.append(f"\n**{str(task_type).upper()}**:")
        for rule in rules or []:
            blocking = "🔴 BLOCKING" if rule.get("blocking") else "⚠️  WARNING"
            desc = rule.get("description", "")
            lines.append(f"  - [{blocking}] {desc}")

    return "\n".join(lines)


def compose_for_role(
    adapter_or_repo_root,
    role: str,
    *,
    config: Optional[Dict] = None,
    active_packs: Optional[List[str]] = None,
) -> str:
    """Compose prompt content for a specific role using composition path resolution.
    
    Uses CompositionPathResolver for consistent path discovery.
    
    Args:
        adapter_or_repo_root: Either an adapter object with repo_root, config, and _active_packs() 
                             method, OR a Path to the repo root.
        role: Role name (e.g., "codex", "claude", "gemini")
        config: Optional config dict (used when adapter_or_repo_root is a Path)
        active_packs: Optional list of active packs (used when adapter_or_repo_root is a Path)
    """
    from ..core import CompositionPathResolver
    from ..includes import resolve_includes
    
    # Handle both adapter objects and direct Path arguments
    if isinstance(adapter_or_repo_root, Path):
        repo_root = adapter_or_repo_root
        cfg = config or {}
        packs = active_packs or []
    else:
        # It's an adapter/engine object
        repo_root = adapter_or_repo_root.repo_root
        cfg = getattr(adapter_or_repo_root, 'config', {}) or {}
        packs = adapter_or_repo_root._active_packs() if hasattr(adapter_or_repo_root, '_active_packs') else []
    
    parts: List[str] = []
    
    # Use composition path resolver
    resolver = CompositionPathResolver(repo_root, "validators")

    core_template = resolver.core_dir / "validators" / "global" / f"{role}.md"
    if core_template.exists():
        parts.append(f"# Edison Core Context for {role}")
        expanded, _ = resolve_includes(core_template.read_text(encoding="utf-8"), core_template)
        parts.append(expanded)

    if packs:
        # Reference shared tech-stack context instead of duplicating pack contexts
        parts.append("\n# Tech-Stack Pack Contexts")
        parts.append("<!-- MANDATORY READ: {{PROJECT_EDISON_DIR}}/core/guidelines/validators/TECH_STACK_CONTEXT.md -->")
        parts.append("")
        parts.append("**Note**: This validator uses tech-stack guidelines from the shared context file.")
        parts.append("The composition engine replaces inline pack duplication with this reference to reduce")
        parts.append("prompt size and maintain DRY principles across all validators.")

    rules_cfg = (cfg or {}).get("rules", {}) or {}
    if rules_cfg.get("enforcement"):
        parts.append("\n# Project Rules")
        parts.append(format_rules_context(rules_cfg))

    # Use composition discovery for overlay
    overlay_path = resolver.project_dir / "validators" / "overlays" / f"{role}.md"
    if overlay_path.exists():
        parts.append("\n# Project Overlay")
        expanded, _ = resolve_includes(overlay_path.read_text(encoding="utf-8"), overlay_path)
        parts.append(expanded)

    content = "\n\n".join(parts)
    if packs:
        content = render_conditional_includes(content, packs)
    return content


__all__ = [
    "format_for_zen",
    "format_rules_context",
    "compose_for_role",
]
