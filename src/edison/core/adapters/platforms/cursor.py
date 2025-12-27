"""Cursor IDE platform adapter.

Handles:
- Syncing agents to .cursor/agents/
- Syncing structured rules to .cursor/rules/
- Managing Cursor directory structure
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.adapters.base import PlatformAdapter
from edison.core.adapters.components.commands import CommandComposer
from edison.core.utils.paths import get_project_config_dir
from edison.core.rules import RulesRegistry
from edison.core.composition.core.errors import RulesCompositionError
from edison.core.utils.io import ensure_directory

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig

class CursorAdapterError(RuntimeError):
    """Error in Cursor adapter operations."""


class CursorAdapter(PlatformAdapter):
    """Platform adapter for Cursor IDE.

    This adapter:
    - Reads from Edison composition system
    - Writes to .cursor/ with Cursor-specific formatting
    - Uses CompositionConfig for all path configuration

    Syncs:
    - .cursor/agents/ (agent files)
    - .cursor/rules/ (structured rules)
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
    ) -> None:
        """Initialize Cursor adapter.

        Args:
            project_root: Project root directory.
            adapter_config: Adapter configuration from loader.
        """
        super().__init__(project_root=project_root, adapter_config=adapter_config)
        self.project_config_dir = get_project_config_dir(self.project_root)

        # Initialize registries
        self.rules_registry = RulesRegistry(project_root=self.project_root)

        # Components (platform-agnostic)
        self.commands = CommandComposer(self.context)

    # =========================================================================
    # Platform Properties
    # =========================================================================

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "cursor"

    # =========================================================================
    # Path Properties
    # =========================================================================

    @property
    def cursor_dir(self) -> Path:
        """Path to .cursor/ directory."""
        return self.get_output_path()

    @property
    def cursor_agents_dir(self) -> Path:
        """Path to .cursor/agents/ directory."""
        return self.cursor_dir / "agents"

    @property
    def cursor_rules_dir(self) -> Path:
        """Path to .cursor/rules/ directory."""
        return self.cursor_dir / "rules"

    @property
    def generated_agents_dir(self) -> Path:
        """Path to _generated/agents/."""
        agents_cfg = self.composition_config.get_content_type("agents")
        if agents_cfg:
            return self.composition_config.resolve_output_path(agents_cfg.output_path)
        return self.project_config_dir / "_generated" / "agents"

    # =========================================================================
    # Validation
    # =========================================================================

    def ensure_structure(self, *, create_missing: bool = True) -> Path:
        """Ensure .cursor directory structure exists.

        Args:
            create_missing: Create directories if they don't exist.

        Returns:
            Path to the .cursor directory.

        Raises:
            CursorAdapterError: If directory doesn't exist and create_missing=False.
        """
        if not self.cursor_dir.exists():
            if not create_missing:
                raise CursorAdapterError(f"Missing: {self.cursor_dir}")
            ensure_directory(self.cursor_dir)

        if not self.cursor_agents_dir.exists():
            if not create_missing:
                raise CursorAdapterError(f"Missing: {self.cursor_agents_dir}")
            ensure_directory(self.cursor_agents_dir)

        if not self.cursor_rules_dir.exists():
            if not create_missing:
                raise CursorAdapterError(f"Missing: {self.cursor_rules_dir}")
            ensure_directory(self.cursor_rules_dir)

        return self.cursor_dir

    # =========================================================================
    # Composition Helpers
    # =========================================================================

    def _group_rules_by_category(self, packs: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Group composed rules by semantic category for structured export."""
        try:
            composed = self.rules_registry.compose(packs=packs)
        except RulesCompositionError:
            return {}

        rules_map: Dict[str, Dict[str, Any]] = composed.get("rules", {}) or {}
        if not rules_map:
            return {}

        target_categories = {"validation", "implementation", "delegation", "context"}
        grouped: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in target_categories}

        for rid in sorted(rules_map.keys()):
            rule = rules_map[rid]
            category = str(rule.get("category") or "").lower()
            if category not in target_categories:
                continue
            grouped[category].append(rule)

        # Drop empty categories
        return {cat: rules for cat, rules in grouped.items() if rules}

    def _render_structured_rule(self, rule: Dict[str, Any]) -> str:
        """Render a single rule into Cursor .mdc front-matter + body format."""
        rid = str(rule.get("id") or "")
        title = str(rule.get("title") or rid)
        category = str(rule.get("category") or "").lower()
        blocking = bool(rule.get("blocking"))
        contexts = rule.get("contexts") or []

        meta: Dict[str, Any] = {
            "id": rid,
            "title": title,
            "category": category,
            "blocking": blocking,
            "contexts": contexts,
        }
        # Preserve additional metadata when present
        if rule.get("origins"):
            meta["origins"] = rule["origins"]
        if rule.get("source"):
            meta["source"] = rule["source"]
        if rule.get("dependencies"):
            meta["dependencies"] = rule["dependencies"]

        from edison.core.utils.text import format_frontmatter

        # Use shared frontmatter formatter for consistency
        frontmatter_str = format_frontmatter(meta, exclude_none=True)

        body = (rule.get("body") or "").strip()
        if not body:
            body = "_No body defined for this rule._"

        sections: List[str] = [
            frontmatter_str.rstrip(),
            "",
            f"# {title}",
            "",
            "## Body",
            body,
        ]

        return "\n".join(sections).rstrip()


    # =========================================================================
    # Sync Methods
    # =========================================================================

    def sync_structured_rules(self) -> List[Path]:
        """Generate structured Cursor rule files under `.cursor/rules/*.mdc`.

        Rules are grouped by high-level category:
          - validation.mdc
          - implementation.mdc
          - delegation.mdc
          - context.mdc

        Returns:
            List of written rule files.
        """
        packs = self.get_active_packs()
        grouped = self._group_rules_by_category(packs)
        if not grouped:
            return []

        ensure_directory(self.cursor_rules_dir)
        written: List[Path] = []

        for category, rules in sorted(grouped.items()):
            path = self.cursor_rules_dir / f"{category}.mdc"
            sections = [self._render_structured_rule(rule) for rule in rules]
            content = "\n\n".join(sections).rstrip() + "\n"
            self.writer.write_text(path, content)
            written.append(path)

        return written

    def sync_agents_to_cursor(self, auto_compose: bool = False) -> List[Path]:
        """Sync composed agents from `<project_config_dir>/_generated/agents` into `.cursor/agents`.

        Args:
            auto_compose: If True and no generated agents found, compose from core templates.

        Returns:
            List of synced agent files.
        """
        src_dir = self.generated_agents_dir

        has_sources = src_dir.exists() and any(src_dir.glob("*.md"))
        if not has_sources and auto_compose:
            from edison.core.composition.registries._types_manager import ComposableTypesManager

            packs = self.get_active_packs()
            types_manager = ComposableTypesManager(project_root=self.project_root)
            types_manager.write_type("agents", packs)
            has_sources = src_dir.exists() and any(src_dir.glob("*.md"))

        if not has_sources:
            return []

        ensure_directory(self.cursor_agents_dir)
        copied: List[Path] = []

        for src in sorted(src_dir.glob("*.md")):
            dest = self.cursor_agents_dir / src.name
            content = src.read_text(encoding="utf-8")
            self.writer.write_text(dest, content)
            copied.append(dest)

        return copied

    def sync_all(self) -> Dict[str, List[Path]]:
        """Execute complete synchronization workflow.

        Syncs:
        - .cursor/rules/*.mdc (structured rules)
        - .cursor/agents/*.md (agents)
        - commands/ for cursor (if configured)

        Returns:
            Dictionary containing sync results with keys:
            - rules: List of structured rule files
            - agents: List of agent files
            - commands: List of command files
        """
        result: Dict[str, List[Path]] = {
            "rules": [],
            "agents": [],
            "commands": [],
        }

        result["rules"] = self.sync_structured_rules()
        result["agents"] = self.sync_agents_to_cursor(auto_compose=True)
        definitions = self.commands.compose()
        commands = self.commands.compose_for_platform("cursor", definitions)
        result["commands"] = list(commands.values())

        return result


__all__ = ["CursorAdapter", "CursorAdapterError"]
