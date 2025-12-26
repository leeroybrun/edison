"""Cursor IDE platform adapter.

Handles:
- Syncing .cursorrules from Edison guidelines/rules
- Syncing agents to .cursor/agents/
- Syncing structured rules to .cursor/rules/
- Managing Cursor directory structure
"""
from __future__ import annotations

import difflib
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.adapters.base import PlatformAdapter
from edison.core.adapters.components.commands import CommandComposer
from edison.core.utils.paths import get_project_config_dir
from edison.core.composition.registries.generic import GenericRegistry
from edison.core.rules import RulesRegistry
from edison.core.composition.core.errors import RulesCompositionError
from edison.core.utils.time import utc_timestamp
from edison.core.utils.io import write_json_atomic, ensure_directory

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig

# Autogen markers for .cursorrules
AUTOGEN_BEGIN = "<!-- EDISON_CURSOR_AUTOGEN:BEGIN -->"
AUTOGEN_END = "<!-- EDISON_CURSOR_AUTOGEN:END -->"


class CursorAdapterError(RuntimeError):
    """Error in Cursor adapter operations."""


class CursorAdapter(PlatformAdapter):
    """Platform adapter for Cursor IDE.

    This adapter:
    - Reads from Edison composition system
    - Writes to .cursorrules and .cursor/ with Cursor-specific formatting
    - Uses CompositionConfig for all path configuration
    - Does composition of guidelines and rules

    Syncs:
    - .cursorrules (unified rules file)
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
        self.guideline_registry = GenericRegistry("guidelines", project_root=self.project_root)
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
    def cursorrules_path(self) -> Path:
        """Path to .cursorrules file."""
        return self.project_root / ".cursorrules"

    @property
    def cursor_agents_dir(self) -> Path:
        """Path to .cursor/agents/ directory."""
        return self.cursor_dir / "agents"

    @property
    def cursor_rules_dir(self) -> Path:
        """Path to .cursor/rules/ directory."""
        return self.cursor_dir / "rules"

    @property
    def cursor_cache_dir(self) -> Path:
        """Path to cache directory for cursor sync metadata."""
        return self.project_config_dir / ".cache" / "cursor"

    @property
    def snapshot_path(self) -> Path:
        """Path to cursorrules snapshot."""
        return self.cursor_cache_dir / "cursorrules.snapshot.md"

    @property
    def snapshot_meta_path(self) -> Path:
        """Path to cursorrules metadata."""
        return self.cursor_cache_dir / "cursorrules.meta.json"

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

    def _compose_guidelines_block(self, packs: List[str]) -> str:
        """Compose guidelines block for .cursorrules."""
        names = self.guideline_registry.list_names(packs)
        if not names:
            return ""

        sections: List[str] = ["## Guidelines"]
        for name in sorted(names):
            text = self.guideline_registry.compose(name, packs) or ""
            body = text.strip()
            sections.append(f"\n### {name}\n\n{body}")

        return "\n".join(sections).rstrip()

    def _compose_rules_block(self, packs: List[str]) -> str:
        """Compose rules block for .cursorrules."""
        try:
            composed = self.rules_registry.compose(packs=packs)
        except RulesCompositionError:
            return ""

        rules_map: Dict[str, Dict[str, Any]] = composed.get("rules", {}) or {}
        if not rules_map:
            return ""

        lines: List[str] = ["## Rules"]
        for rid in sorted(rules_map.keys()):
            rule = rules_map[rid]
            title = str(rule.get("title") or rid)
            blocking = bool(rule.get("blocking"))
            contexts = rule.get("contexts") or []
            body = (rule.get("body") or "").strip()

            level = "BLOCKING" if blocking else "NON-BLOCKING"
            heading = f"\n### {title} ({rid})\n"
            lines.append(heading)
            lines.append(f"- Level: {level}")
            if contexts:
                ctx_str = ", ".join(str(c) for c in contexts)
                lines.append(f"- Contexts: {ctx_str}")
            if body:
                lines.append("\n" + body)

        return "\n".join(lines).rstrip()

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

    def _render_cursorrules(self) -> str:
        """Render full `.cursorrules` content with autogen markers."""
        packs = self.get_active_packs()
        guidelines_block = self._compose_guidelines_block(packs)
        rules_block = self._compose_rules_block(packs)

        header_lines = [
            "# Edison Cursor Rules",
            "",
            "<!-- GENERATED BY EDISON CURSOR ADAPTER -->",
            f"<!-- Generated: {utc_timestamp()} -->",
            "<!-- Manual edits outside AUTOGEN markers are preserved on re-sync -->",
            "",
            AUTOGEN_BEGIN,
            "",
        ]

        body_parts: List[str] = []
        if guidelines_block:
            body_parts.append(guidelines_block)
        if rules_block:
            if body_parts:
                body_parts.append("")
            body_parts.append(rules_block)

        if not body_parts:
            body_parts.append("_No guidelines or rules are currently defined in Edison._")

        footer_lines = [
            "",
            AUTOGEN_END,
            "",
        ]

        return "\n".join(header_lines + body_parts + footer_lines).rstrip() + "\n"

    @staticmethod
    def _split_autogen_block(text: str) -> tuple[str, str, str]:
        """Split text into (prefix, autogen_block, suffix) using markers.

        When markers are not present, the entire text is returned as the
        prefix and the other parts are empty.
        """
        start = text.find(AUTOGEN_BEGIN)
        if start == -1:
            return text, "", ""
        end = text.find(AUTOGEN_END, start)
        if end == -1:
            return text, "", ""
        end += len(AUTOGEN_END)
        prefix = text[:start]
        block = text[start:end]
        suffix = text[end:]
        return prefix, block, suffix

    def _write_snapshot(self, content: str, generated_hash: str) -> None:
        """Write snapshot of cursorrules to cache."""
        ensure_directory(self.cursor_cache_dir)
        self.writer.write_text(self.snapshot_path, content)
        meta = {
            "generatedAt": utc_timestamp(),
            "hash": generated_hash,
        }
        write_json_atomic(self.snapshot_meta_path, meta, indent=2)

    def merge_cursor_overrides(self, generated_content: str) -> str:
        """Merge generated content with existing `.cursorrules`.

        When both the existing file and generated content contain the
        AUTOGEN markers, only the AUTOGEN block is replaced and the
        existing prefix/suffix are preserved. When markers are missing
        (e.g. hand-written file), the generated content is appended
        after the existing text to avoid clobbering manual sections.
        """
        path = self.cursorrules_path
        if not path.exists():
            return generated_content

        current = path.read_text(encoding="utf-8")
        cur_prefix, cur_block, cur_suffix = self._split_autogen_block(current)
        gen_prefix, gen_block, gen_suffix = self._split_autogen_block(generated_content)

        # If both texts have an identifiable autogen block, splice new block in place.
        if cur_block and gen_block:
            return (cur_prefix or gen_prefix) + gen_block + (cur_suffix or gen_suffix)

        # Fallback: append generated content after existing text separated by a blank line.
        merged = current.rstrip() + "\n\n" + generated_content.lstrip()
        return merged

    def detect_cursor_overrides(self) -> Dict[str, Any]:
        """Detect manual edits to `.cursorrules` since the last sync.

        Compares the current `.cursorrules` to the last snapshot captured by
        `sync_to_cursorrules()` and returns a diff report.
        """
        report: Dict[str, Any] = {
            "fileExists": self.cursorrules_path.exists(),
            "snapshotExists": self.snapshot_path.exists(),
            "metaExists": self.snapshot_meta_path.exists(),
            "has_overrides": False,
            "diff": [],
        }

        if not report["fileExists"] or not report["snapshotExists"]:
            return report

        current = self.cursorrules_path.read_text(encoding="utf-8")
        snapshot = self.snapshot_path.read_text(encoding="utf-8")

        if current == snapshot:
            return report

        diff = list(
            difflib.unified_diff(
                snapshot.splitlines(),
                current.splitlines(),
                fromfile=str(self.snapshot_path),
                tofile=str(self.cursorrules_path),
                lineterm="",
            )
        )

        report["has_overrides"] = True
        report["diff"] = diff
        return report

    # =========================================================================
    # Sync Methods
    # =========================================================================

    def sync_to_cursorrules(self) -> Path:
        """Generate or update `.cursorrules` from Edison guidelines/rules.

        Manual edits outside the AUTOGEN markers are preserved across
        syncs. Manual edits within the AUTOGEN block are overwritten by
        design and should be avoided.

        Returns:
            Path to the .cursorrules file.
        """
        generated = self._render_cursorrules()
        gen_hash = hashlib.sha256(generated.encode("utf-8")).hexdigest()

        current = None
        if self.cursorrules_path.exists():
            current = self.cursorrules_path.read_text(encoding="utf-8")

        # Initial sync or regeneration when no existing file: write directly.
        if current is None:
            final = generated
        else:
            # Attempt conservative merge preserving manual sections.
            final = self.merge_cursor_overrides(generated_content=generated)

        self.writer.write_text(self.cursorrules_path, final)
        self._write_snapshot(final, gen_hash)
        return self.cursorrules_path

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
        - .cursorrules (guidelines + rules)
        - .cursor/rules/*.mdc (structured rules)
        - .cursor/agents/*.md (agents)
        - commands/ for cursor (if configured)

        Returns:
            Dictionary containing sync results with keys:
            - cursorrules: List with .cursorrules path
            - rules: List of structured rule files
            - agents: List of agent files
            - commands: List of command files
        """
        result: Dict[str, List[Path]] = {
            "cursorrules": [],
            "rules": [],
            "agents": [],
            "commands": [],
        }

        cursorrules_path = self.sync_to_cursorrules()
        result["cursorrules"].append(cursorrules_path)

        result["rules"] = self.sync_structured_rules()
        result["agents"] = self.sync_agents_to_cursor(auto_compose=True)
        definitions = self.commands.compose()
        commands = self.commands.compose_for_platform("cursor", definitions)
        result["commands"] = list(commands.values())

        return result


__all__ = ["CursorAdapter", "CursorAdapterError", "AUTOGEN_BEGIN", "AUTOGEN_END"]
