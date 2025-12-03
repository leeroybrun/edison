"""Cursor Sync Adapter (full-featured).

Complete integration layer between the Edison composition system
and Cursor's configuration surface:
  - `.cursorrules` (Markdown rules file)
  - `.cursor/agents/` (per-agent Markdown briefs)

Responsibilities:
  - Compose a unified `.cursorrules` file from Edison guidelines/rules
  - Detect manual edits to `.cursorrules` since the last sync
  - Merge generated content while preserving manual sections by default
  - Sync composed agents from `<project_config_dir>/_generated/agents/` into
    `.cursor/agents/`
"""
from __future__ import annotations

import difflib
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import SyncAdapter
from edison.core.utils.paths import get_project_config_dir
from ...composition.registries import agents as _agents
from ...composition import GuidelineRegistry
from ...composition.output.writer import CompositionFileWriter
from ...rules import RulesRegistry, RulesCompositionError  # type: ignore
from ...utils.time import utc_timestamp
from edison.core.utils.io import write_json_atomic, ensure_directory

AgentRegistry = _agents.AgentRegistry
AgentError = _agents.AgentError
compose_agent = _agents.compose_agent


AUTOGEN_BEGIN = "<!-- EDISON_CURSOR_AUTOGEN:BEGIN -->"
AUTOGEN_END = "<!-- EDISON_CURSOR_AUTOGEN:END -->"


class CursorSync(SyncAdapter):
    """Adapter between Edison composition and Cursor config files.

    Inherits from SyncAdapter which provides:
    - repo_root resolution via PathResolver
    - config property via ConfigMixin
    - active_packs property via ConfigMixin
    - packs_config property via ConfigMixin
    """

    last_auto_composed_agents: int = 0

    def __init__(
        self,
        project_root: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(repo_root=project_root)

        # Merge any passed config with loaded config
        if config:
            from edison.core.config import ConfigManager
            self._cached_config = ConfigManager(self.repo_root).deep_merge(
                self.config, config
            )

        self.project_config_dir = get_project_config_dir(self.repo_root)
        self.guideline_registry = GuidelineRegistry(repo_root=self.repo_root)
        self.rules_registry = RulesRegistry(project_root=self.repo_root)
        self.last_auto_composed_agents = 0
        self._writer: Optional[CompositionFileWriter] = None

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    @property
    def _cursorrules_path(self) -> Path:
        return self.repo_root / ".cursorrules"

    @property
    def _cursor_agents_dir(self) -> Path:
        from edison.core.config.domains import AdaptersConfig
        adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
        cursor_dir = adapters_cfg.get_client_path("cursor")
        return cursor_dir / "agents"

    @property
    def _cursor_rules_dir(self) -> Path:
        from edison.core.config.domains import AdaptersConfig
        adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
        cursor_dir = adapters_cfg.get_client_path("cursor")
        return cursor_dir / "rules"

    @property
    def _cursor_cache_dir(self) -> Path:
        return self.project_config_dir / ".cache" / "cursor"

    @property
    def _snapshot_path(self) -> Path:
        return self._cursor_cache_dir / "cursorrules.snapshot.md"

    @property
    def _snapshot_meta_path(self) -> Path:
        return self._cursor_cache_dir / "cursorrules.meta.json"

    @property
    def writer(self) -> CompositionFileWriter:
        """Lazy-initialized file writer for composition outputs."""
        if self._writer is None:
            self._writer = CompositionFileWriter(base_dir=self.repo_root)
        return self._writer

    # ------------------------------------------------------------------
    # Internal helpers (use ConfigMixin properties)
    # ------------------------------------------------------------------
    def _get_active_packs(self) -> List[str]:
        """Get active packs via ConfigMixin."""
        return self.active_packs

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

    def _compose_guidelines_block(self, packs: List[str]) -> str:
        names = self.guideline_registry.all_names(packs, include_project=True)
        if not names:
            return ""

        sections: List[str] = ["## Guidelines"]
        for name in sorted(names):
            result = self.guideline_registry.compose(name, packs, project_overrides=True)
            body = result.text.strip()
            sections.append(f"\n### {name}\n\n{body}")

        return "\n".join(sections).rstrip()

    def _compose_rules_block(self, packs: List[str]) -> str:
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
        packs = self._get_active_packs()
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

    def _write_snapshot(self, content: str, generated_hash: str) -> None:
        ensure_directory(self._cursor_cache_dir)
        self.writer.write_text(self._snapshot_path, content)
        meta = {
            "generatedAt": utc_timestamp(),
            "hash": generated_hash,
        }
        write_json_atomic(self._snapshot_meta_path, meta, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def sync_to_cursorrules(self) -> Path:
        """Generate or update `.cursorrules` from Edison guidelines/rules.

        Manual edits outside the AUTOGEN markers are preserved across
        syncs. Manual edits within the AUTOGEN block are overwritten by
        design and should be avoided.
        """
        generated = self._render_cursorrules()
        gen_hash = hashlib.sha256(generated.encode("utf-8")).hexdigest()

        current = None
        if self._cursorrules_path.exists():
            current = self._cursorrules_path.read_text(encoding="utf-8")

        # Initial sync or regeneration when no existing file: write directly.
        if current is None:
            final = generated
        else:
            # Attempt conservative merge preserving manual sections.
            final = self.merge_cursor_overrides(generated_content=generated)

        self.writer.write_text(self._cursorrules_path, final)
        self._write_snapshot(final, gen_hash)
        return self._cursorrules_path

    def sync_structured_rules(self) -> List[Path]:
        """Generate structured Cursor rule files under `.cursor/rules/*.mdc`.

        Rules are grouped by high-level category:
          - validation.mdc
          - implementation.mdc
          - delegation.mdc
          - context.mdc
        """
        packs = self._get_active_packs()
        grouped = self._group_rules_by_category(packs)
        if not grouped:
            return []

        ensure_directory(self._cursor_rules_dir)
        written: List[Path] = []

        for category, rules in sorted(grouped.items()):
            path = self._cursor_rules_dir / f"{category}.mdc"
            sections = [self._render_structured_rule(rule) for rule in rules]
            content = "\n\n".join(sections).rstrip() + "\n"
            self.writer.write_text(path, content)
            written.append(path)

        return written

    def detect_cursor_overrides(self) -> Dict[str, Any]:
        """Detect manual edits to `.cursorrules` since the last sync.

        Returns a small report dictionary suitable for CLI presentation:
          {
            "path": "<absolute-path>",
            "fileExists": bool,
            "snapshotExists": bool,
            "has_overrides": bool,
            "diff": ["...unified diff lines..."],
          }
        """
        path = self._cursorrules_path
        report: Dict[str, Any] = {
            "path": str(path),
            "fileExists": path.exists(),
            "snapshotExists": self._snapshot_path.exists(),
            "has_overrides": False,
            "diff": [],
        }

        if not path.exists() or not self._snapshot_path.exists():
            return report

        baseline = self._snapshot_path.read_text(encoding="utf-8")
        current = path.read_text(encoding="utf-8")
        if baseline == current:
            return report

        diff = list(
            difflib.unified_diff(
                baseline.splitlines(),
                current.splitlines(),
                fromfile="snapshot",
                tofile=".cursorrules",
                lineterm="",
            )
        )
        report["has_overrides"] = True
        report["diff"] = diff
        return report

    def merge_cursor_overrides(self, generated_content: str) -> str:
        """Merge generated content with existing `.cursorrules`.

        When both the existing file and generated content contain the
        AUTOGEN markers, only the AUTOGEN block is replaced and the
        existing prefix/suffix are preserved. When markers are missing
        (e.g. hand-written file), the generated content is appended
        after the existing text to avoid clobbering manual sections.
        """
        path = self._cursorrules_path
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

    def _auto_compose_agents(self, src_dir: Path) -> int:
        """Compose agents into `<project_config_dir>/_generated/agents` when missing."""
        registry = AgentRegistry(project_root=self.repo_root)
        core_agents = registry.discover_core()
        if not core_agents:
            return 0

        packs = self._get_active_packs()
        ensure_directory(src_dir)

        count = 0
        for name in sorted(core_agents.keys()):
            try:
                text = compose_agent(name, packs=packs, project_root=self.repo_root)
            except AgentError:
                continue
            out_file = src_dir / f"{name}.md"
            self.writer.write_text(out_file, text)
            count += 1
        return count

    def sync_agents_to_cursor(self, auto_compose: bool = False) -> List[Path]:
        """Sync composed agents from `<project_config_dir>/_generated/agents` into `.cursor/agents`.

        When ``auto_compose`` is True and no generated agents are found,
        this method composes agents from core templates (plus pack/project
        overlays) before syncing them into `.cursor/agents`.
        """
        src_dir = self.project_config_dir / "_generated" / "agents"
        self.last_auto_composed_agents = 0

        has_sources = src_dir.exists() and any(src_dir.glob("*.md"))
        if not has_sources and auto_compose:
            self.last_auto_composed_agents = self._auto_compose_agents(src_dir)
            has_sources = src_dir.exists() and any(src_dir.glob("*.md"))

        if not has_sources:
            return []

        ensure_directory(self._cursor_agents_dir)
        copied: List[Path] = []

        for src in sorted(src_dir.glob("*.md")):
            dest = self._cursor_agents_dir / src.name
            content = src.read_text(encoding="utf-8")
            self.writer.write_text(dest, content)
            copied.append(dest)

        return copied

    def sync_all(self) -> Dict[str, Any]:
        """Execute complete synchronization workflow.

        Syncs:
        - .cursorrules (guidelines + rules)
        - .cursor/rules/*.mdc (structured rules)
        - .cursor/agents/*.md (agents)

        Returns:
            Dictionary containing sync results.
        """
        result: Dict[str, Any] = {
            "cursorrules": [],
            "rules": [],
            "agents": [],
        }

        cursorrules_path = self.sync_to_cursorrules()
        result["cursorrules"].append(cursorrules_path)

        result["rules"] = self.sync_structured_rules()
        result["agents"] = self.sync_agents_to_cursor(auto_compose=True)

        return result


__all__ = [
    "CursorSync",
    "AUTOGEN_BEGIN",
    "AUTOGEN_END",
]
