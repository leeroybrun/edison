"""
Rules Registry for the Edison Rules system.

This module provides the RulesRegistry class for loading and composing rules
from bundled + pack YAML registries, with support for guideline anchors and
include resolution.

Architecture:
    - Bundled rules: edison.data/rules/registry.yml (ALWAYS used for core)
    - Pack rules: <project-config-dir>/packs/<pack>/rules/registry.yml
    - Project rules: <project-config-dir>/rules/registry.yml (overrides)

Uses ConfigManager for pack directory resolution to maintain consistency
with the unified configuration system.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from edison.core.composition.core.sections import SectionParser
from edison.core.utils.paths import EdisonPathError, PathResolver
from edison.core.utils.io import read_yaml

from edison.core.composition.core.errors import AnchorNotFoundError, RulesCompositionError
from edison.data import get_data_path
from edison.core.utils.profiling import span


class RulesRegistry:
    """
    Load and compose rules from bundled + pack YAML registries.

    Features:
    - YAML-based rule loading
    - Anchor extraction from guidelines
    - Include resolution
    - Uses ConfigManager for pack directory resolution

    Registry locations:
      - Bundled: edison.data/rules/registry.yml (ALWAYS used for core)
      - Packs: <project-config-dir>/packs/<pack>/rules/registry.yml (bundled + project)
      - Project: <project-config-dir>/rules/registry.yml (overrides)

    This class is read-only; it does not mutate project state.
    """

    entity_type: str = "rule"

    def __init__(self, project_root: Optional[Path] = None) -> None:
        try:
            self.project_root = project_root or PathResolver.resolve_project_root()
        except (EdisonPathError, ValueError) as exc:
            raise RulesCompositionError(str(exc)) from exc

        # Use ConfigManager for consistent pack directory resolution
        from edison.core.config import ConfigManager

        cfg_mgr = ConfigManager(repo_root=self.project_root)

        # Project config directory (e.g. <project-config-dir>, configurable)
        self.project_dir = cfg_mgr.project_config_dir.parent

        # Pack directories from ConfigManager (unified source of truth)
        self.bundled_packs_dir = cfg_mgr.bundled_packs_dir
        self.project_packs_dir = cfg_mgr.project_packs_dir

        # Core registry is ALWAYS from bundled data
        self.core_registry_path = get_data_path("rules", "registry.yml")

        # Bundled data directory for resolving guideline paths
        self.bundled_data_dir = Path(get_data_path(""))

        # Store reference to config manager for active packs lookup
        self._cfg_mgr = cfg_mgr
        self._types_manager: Optional["ComposableTypesManager"] = None  # type: ignore[name-defined]

    def get_active_packs(self) -> List[str]:
        """Get active packs from ConfigManager.

        Returns:
            List of active pack names from packs.active config.
        """
        cfg = self._cfg_mgr.load_config(validate=False, include_packs=False)
        packs_section = cfg.get("packs", {}) or {}
        active = packs_section.get("active", []) or []
        return [str(p) for p in active if p] if isinstance(active, list) else []

    def _get_types_manager(self) -> "ComposableTypesManager":  # type: ignore[name-defined]
        """Lazy ComposableTypesManager for composed-include resolution."""
        if self._types_manager is None:
            from edison.core.composition.registries._types_manager import ComposableTypesManager

            self._types_manager = ComposableTypesManager(project_root=self.project_root)
        return self._types_manager

    def _build_include_provider(self, packs: List[str]) -> Callable[[str], Optional[str]]:
        """Build a composed include provider (no legacy include resolver)."""
        from edison.core.composition.includes import ComposedIncludeProvider

        return ComposedIncludeProvider(
            types_manager=self._get_types_manager(),
            packs=tuple(packs),
            materialize=False,
        ).build()

    def _load_yaml_file(self, path: Path, required: bool = True) -> Any:
        """Load a single YAML file using shared utility.
        
        Args:
            path: Path to YAML file
            required: If True, raise FileNotFoundError when file doesn't exist
            
        Returns:
            Parsed YAML content
        """
        if not path.exists():
            if required:
                raise FileNotFoundError(f"YAML file not found: {path}")
            return {}
        
        return read_yaml(path, default={})

    # ------- Utility Methods -------

    @staticmethod
    def extract_section_content(source_file: Path, section_name: str) -> str:
        """
        Extract content between SECTION markers in a guideline file.

        Uses SectionParser to extract content from <!-- SECTION: name --> markers.

        Args:
            source_file: Path to the guideline file
            section_name: Name of the section to extract

        Returns:
            The content between the section markers

        Raises:
            FileNotFoundError: If the source file doesn't exist
            AnchorNotFoundError: If the section isn't found in the file
        """
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        content = source_file.read_text(encoding="utf-8")
        parser = SectionParser()
        section_content = parser.extract_section(content, section_name)
        
        if section_content is None:
            raise AnchorNotFoundError(f"Section '{section_name}' not found in {source_file}")
        
        return section_content

    # ------- Registry Interface Implementation -------

    def discover_core(self) -> Dict[str, Dict[str, Any]]:
        """Discover core rules from bundled registry."""
        registry = self.load_core_registry()
        rules = registry.get("rules", [])
        return {rule.get("id", f"rule-{i}"): rule for i, rule in enumerate(rules) if isinstance(rule, dict)}
    
    def discover_packs(self, packs: List[str]) -> Dict[str, Dict[str, Any]]:
        """Discover rules from active packs (bundled + project)."""
        result: Dict[str, Dict[str, Any]] = {}
        for pack in packs:
            registry = self.load_pack_registry(pack)
            rules = registry.get("rules", [])
            for i, rule in enumerate(rules):
                if isinstance(rule, dict):
                    rule_id = rule.get("id", f"{pack}-rule-{i}")
                    result[rule_id] = rule
        return result
    
    def discover_project(self) -> Dict[str, Dict[str, Any]]:
        """Discover project-level rule overrides at <project-config-dir>/rules/."""
        path = self.project_dir / "rules" / "registry.yml"
        registry = self._load_yaml(path, required=False)
        rules = registry.get("rules", [])
        return {rule.get("id", f"project-rule-{i}"): rule for i, rule in enumerate(rules) if isinstance(rule, dict)}
    
    def exists(self, rule_id: str) -> bool:
        """Check if a rule exists in core registry."""
        return rule_id in self.discover_core()
    
    def get(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a rule by ID from core registry."""
        return self.discover_core().get(rule_id)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all rules from core registry."""
        return list(self.discover_core().values())

    # ------------------------------------------------------------------
    # Registry loading
    # ------------------------------------------------------------------
    def _load_yaml(self, path: Path, *, required: bool) -> Dict[str, Any]:
        """Load and validate rules YAML file."""
        try:
            data = self._load_yaml_file(path, required=required)
        except FileNotFoundError:
            if required:
                raise RulesCompositionError(f"Rules registry not found at {path}")
            return {"version": None, "rules": []}

        if not isinstance(data, dict):
            raise RulesCompositionError(
                f"Invalid rules registry at {path}: expected mapping at top level"
            )

        rules = data.get("rules") or []
        if not isinstance(rules, list):
            raise RulesCompositionError(
                f"Invalid rules registry at {path}: 'rules' must be a list"
            )
        data["rules"] = rules
        return data

    def load_core_registry(self) -> Dict[str, Any]:
        """Load bundled rules registry from edison.data package."""
        return self._load_yaml(self.core_registry_path, required=True)

    def load_pack_registry(self, pack_name: str) -> Dict[str, Any]:
        """Load pack-specific rules registry, merging bundled + project.

        Architecture:
        - Bundled pack rules: edison.data/packs/<pack>/rules/registry.yml (base)
        - Project pack rules: <project-config-dir>/packs/<pack>/rules/registry.yml (extends/overrides)
        - Merge strategy: project rules are appended to bundled rules
        """
        # Load bundled pack registry (base layer)
        bundled_path = self.bundled_packs_dir / pack_name / "rules" / "registry.yml"
        bundled_registry = self._load_yaml(bundled_path, required=False)

        # Load project pack registry (override layer)
        project_path = self.project_packs_dir / pack_name / "rules" / "registry.yml"
        project_registry = self._load_yaml(project_path, required=False)

        # If only one exists, return it
        if not bundled_registry.get("rules"):
            return project_registry
        if not project_registry.get("rules"):
            return bundled_registry

        # Merge: combine rules from both registries
        # Project rules are appended (they can override by having same ID)
        merged_rules = list(bundled_registry.get("rules", []))
        merged_rules.extend(project_registry.get("rules", []))

        return {
            "version": project_registry.get("version") or bundled_registry.get("version") or "1.0.0",
            "rules": merged_rules,
        }

    # ------------------------------------------------------------------
    # Composition helpers
    # ------------------------------------------------------------------
    def _resolve_source(self, rule: Dict[str, Any]) -> Tuple[Optional[Path], Optional[str]]:
        """Resolve source file path and optional anchor for a rule."""
        source = rule.get("source") or {}
        file_ref = str(source.get("file") or rule.get("sourcePath") or "").strip()
        anchor = source.get("anchor")

        if not file_ref:
            return None, None

        # Legacy form: "path#anchor" embedded in sourcePath
        file_part, sep, frag = file_ref.partition("#")
        if sep and frag and not anchor:
            anchor = frag
        else:
            file_part = file_ref

        # Resolve file path - prefer _generated (final composed) over bundled (source)
        source_path: Optional[Path] = None
        
        # Project-relative paths starting with project config dir (preferred).
        project_prefix = f"{self.project_dir.name}/"
        legacy_prefix = ".edison/"

        if file_part.startswith(project_prefix) or file_part.startswith(legacy_prefix):
            # Normalize legacy ".edison/..." references to the configured project dir.
            if file_part.startswith(legacy_prefix) and self.project_dir.name != ".edison":
                normalized_rel = file_part[len(legacy_prefix) :]
                project_path = (self.project_dir / normalized_rel).resolve()
            else:
                project_path = (self.project_root / file_part).resolve()
            if project_path.exists():
                source_path = project_path
            else:
                # Fall back to bundled data if project file doesn't exist
                # Convert <project_dir>/_generated/X to X for bundled lookup
                bundled_ref = file_part
                if "/_generated/" in bundled_ref:
                    bundled_ref = bundled_ref.split("/_generated/", 1)[1]
                elif bundled_ref.startswith(project_prefix):
                    bundled_ref = bundled_ref[len(project_prefix) :]
                elif bundled_ref.startswith(legacy_prefix):
                    bundled_ref = bundled_ref[len(legacy_prefix) :]
                bundled_path = (self.bundled_data_dir / bundled_ref).resolve()
                if bundled_path.exists():
                    source_path = bundled_path
                else:
                    # If neither exists, use project path (will error on read)
                    source_path = project_path
        # Absolute paths
        elif file_part.startswith("/"):
            source_path = (self.project_root / file_part.lstrip("/")).resolve()
        else:
            # Relative paths: resolve to _generated first (final composed content),
            # then fall back to bundled data (source templates)
            # This ensures agents read the final composed guidelines, not source templates
            generated_path = (self.project_dir / "_generated" / file_part).resolve()
            if generated_path.exists():
                source_path = generated_path
            else:
                # Fall back to bundled data for development/testing scenarios
                bundled_path = (self.bundled_data_dir / file_part).resolve()
                if bundled_path.exists():
                    source_path = bundled_path
                else:
                    # Last resort: project directory
                    project_path = (self.project_dir / file_part).resolve()
                    source_path = project_path

        return source_path, str(anchor) if anchor else None

    def _compose_rule_body(
        self,
        rule: Dict[str, Any],
        origin: str,
        packs: List[str],
        *,
        deps: Optional[Set[str]] = None,
        resolve_sources: bool = True,
    ) -> Tuple[str, List[str]]:
        """
        Build composed body text for a single rule.

        Composition semantics:
          - If source.file (+ optional anchor) is present, extract anchor content
            or entire file, then resolve {{include:...}} patterns via the
            prompt composition engine.
          - Append inline ``guidance`` text after resolved anchor content.
        """
        if deps is None:
            deps = set()

        source_file, anchor = self._resolve_source(rule)

        body_parts: List[str] = []

        # IMPORTANT: Rules must stay small and context-friendly.
        # We only embed SOURCE content when an explicit anchor is provided.
        # Without an anchor, embedding the whole file is almost always wrong and
        # can explode constitution sizes. In that case, rely on `guidance`.
        if resolve_sources and source_file is not None and anchor:
            with span("rules.compose.anchor", origin=origin, anchor=str(anchor)):
                anchor_text = self.extract_section_content(source_file, anchor)
                body_parts.append(anchor_text)

        guidance = rule.get("guidance")
        if guidance:
            guidance_text = str(guidance).rstrip()
            if guidance_text:
                if body_parts and not body_parts[-1].endswith("\n"):
                    body_parts[-1] += "\n"
                body_parts.append(guidance_text + "\n")

        body = "".join(body_parts) if body_parts else ""

        # Resolve template includes/sections via the unified TemplateEngine pipeline.
        # We only run the template engine when sources were embedded OR when the
        # body contains include directives. This keeps rule composition cheap and
        # avoids accidentally expanding large source files when resolve_sources=False.
        if resolve_sources and ("{{include" in body or "{{include-section" in body or "{{include-if" in body):
            from edison.core.composition.engine import TemplateEngine

            include_provider = self._build_include_provider(packs)
            cfg = self._cfg_mgr.load_config(validate=False, include_packs=True)

            engine = TemplateEngine(
                config=cfg,
                packs=packs,
                project_root=self.project_root,
                # Includes are authored relative to bundled data root.
                source_dir=self.bundled_data_dir,
                include_provider=include_provider,
                strip_section_markers=True,
            )

            composed, report = engine.process(
                body,
                entity_name=str(rule.get("id") or "unknown"),
                entity_type="rules",
            )

            # Fail-closed if include resolution surfaced errors.
            if "<!-- ERROR:" in composed:
                raise RulesCompositionError(f"Include resolution error while composing rule: {rule.get('id')}")

            # Track dependencies (paths/sections) for traceability.
            deps.update(report.includes_resolved)
            deps.update(report.sections_extracted)

            body = composed

        return body, sorted(deps)

    def compose(
        self,
        packs: Optional[List[str]] = None,
        *,
        resolve_sources: bool = False,
    ) -> Dict[str, Any]:
        """
        Compose rules from bundled core + optional packs into a single structure.

        Returns:
            Dict with keys:
              - version: registry version (string)
              - packs: list of packs used during composition
              - rules: mapping of rule-id -> composed rule payload
        """
        packs = list(packs or [])

        with span("rules.compose.total", resolve_sources=resolve_sources, packs=len(packs)):
            core = self.load_core_registry()
        rules_index: Dict[str, Dict[str, Any]] = {}

        # Core rules first (from bundled data)
        for raw_rule in core.get("rules", []) or []:
            if not isinstance(raw_rule, dict):
                continue
            rid = str(raw_rule.get("id") or "").strip()
            if not rid:
                continue

            with span("rules.compose.rule", origin="core", id=rid):
                body, deps = self._compose_rule_body(
                    raw_rule,
                    origin="core",
                    packs=packs,
                    resolve_sources=resolve_sources,
                )
            source_obj: Dict[str, Any] = raw_rule.get("source") or {}
            if not source_obj and raw_rule.get("sourcePath"):
                source_obj = {"file": raw_rule.get("sourcePath")}

            entry: Dict[str, Any] = {
                "id": rid,
                "title": raw_rule.get("title") or rid,
                "category": raw_rule.get("category") or "",
                "blocking": bool(raw_rule.get("blocking", False)),
                "contexts": raw_rule.get("contexts") or [],
                "applies_to": raw_rule.get("applies_to") or [],
                "source": source_obj,
                "guidance": raw_rule.get("guidance"),
                "body": body,
                "origins": ["core"],
                "dependencies": [str(p) for p in deps],
                "_body_resolved": bool(resolve_sources),
            }
            rules_index[rid] = entry

        # Pack overlays merge by rule id
        for pack_name in packs:
            with span("rules.compose.pack", pack=pack_name):
                pack_registry = self.load_pack_registry(pack_name)
            for raw_rule in pack_registry.get("rules", []) or []:
                if not isinstance(raw_rule, dict):
                    continue
                rid = str(raw_rule.get("id") or "").strip()
                if not rid:
                    continue

                with span("rules.compose.rule", origin=f"pack:{pack_name}", id=rid):
                    body, deps = self._compose_rule_body(
                        raw_rule,
                        origin=f"pack:{pack_name}",
                        packs=packs,
                        resolve_sources=resolve_sources,
                    )

                source_obj: Dict[str, Any] = raw_rule.get("source") or {}
                if not source_obj and raw_rule.get("sourcePath"):
                    source_obj = {"file": raw_rule.get("sourcePath")}

                if rid not in rules_index:
                    rules_index[rid] = {
                        "id": rid,
                        "title": raw_rule.get("title") or rid,
                        "category": raw_rule.get("category") or "",
                        "blocking": bool(raw_rule.get("blocking", False)),
                        "contexts": raw_rule.get("contexts") or [],
                        "applies_to": raw_rule.get("applies_to") or [],
                        "source": source_obj,
                        "guidance": raw_rule.get("guidance"),
                        "body": body,
                        "origins": [f"pack:{pack_name}"],
                        "dependencies": [str(p) for p in deps],
                        "_body_resolved": bool(resolve_sources),
                    }
                    continue

                entry = rules_index[rid]
                # Title: allow pack to refine title when provided
                if raw_rule.get("title"):
                    entry["title"] = raw_rule["title"]
                # Category: allow pack to refine category when provided
                if raw_rule.get("category"):
                    entry["category"] = raw_rule["category"]
                # Blocking: once blocking, always blocking
                if raw_rule.get("blocking", False):
                    entry["blocking"] = True
                # Contexts: append pack contexts
                if raw_rule.get("contexts"):
                    entry["contexts"] = (entry.get("contexts") or []) + raw_rule["contexts"]  # type: ignore[index]
                # Applies-to: union (pack may broaden applicability)
                if raw_rule.get("applies_to"):
                    existing_roles = set(entry.get("applies_to") or [])
                    for role in raw_rule["applies_to"]:
                        if role:
                            existing_roles.add(role)
                    entry["applies_to"] = sorted(existing_roles)
                # Source: allow pack to specify/override source when provided
                if raw_rule.get("source") or raw_rule.get("sourcePath"):
                    entry["source"] = source_obj

                # Body: append pack guidance after core text
                entry["body"] = (entry.get("body") or "") + (body or "")
                if raw_rule.get("guidance"):
                    # Track guidance separately so we can re-compose a full body later if needed.
                    prior = (entry.get("guidance") or "")
                    if prior:
                        entry["guidance"] = str(prior).rstrip() + "\n" + str(raw_rule["guidance"]).rstrip()
                    else:
                        entry["guidance"] = raw_rule["guidance"]
                # Origins: record pack contribution
                entry.setdefault("origins", []).append(f"pack:{pack_name}")
                # Dependencies: merge without duplicates
                existing = set(entry.get("dependencies") or [])
                for p in deps:
                    existing.add(str(p))
                entry["dependencies"] = sorted(existing)
                # Body resolution status
                entry["_body_resolved"] = bool(entry.get("_body_resolved")) and bool(resolve_sources)

        # Project overlays (highest precedence) merge by rule id
        with span("rules.compose.project"):
            project_registry = self._load_yaml(self.project_dir / "rules" / "registry.yml", required=False)

        for raw_rule in project_registry.get("rules", []) or []:
            if not isinstance(raw_rule, dict):
                continue
            rid = str(raw_rule.get("id") or "").strip()
            if not rid:
                continue

            with span("rules.compose.rule", origin="project", id=rid):
                body, deps = self._compose_rule_body(
                    raw_rule,
                    origin="project",
                    packs=packs,
                    resolve_sources=resolve_sources,
                )

            source_obj: Dict[str, Any] = raw_rule.get("source") or {}
            if not source_obj and raw_rule.get("sourcePath"):
                source_obj = {"file": raw_rule.get("sourcePath")}

            if rid not in rules_index:
                rules_index[rid] = {
                    "id": rid,
                    "title": raw_rule.get("title") or rid,
                    "category": raw_rule.get("category") or "",
                    "blocking": bool(raw_rule.get("blocking", False)),
                    "contexts": raw_rule.get("contexts") or [],
                    "applies_to": raw_rule.get("applies_to") or [],
                    "source": source_obj,
                    "guidance": raw_rule.get("guidance"),
                    "body": body,
                    "origins": ["project"],
                    "dependencies": [str(p) for p in deps],
                    "_body_resolved": bool(resolve_sources),
                }
                continue

            entry = rules_index[rid]
            if raw_rule.get("title"):
                entry["title"] = raw_rule["title"]
            if raw_rule.get("category"):
                entry["category"] = raw_rule["category"]
            if raw_rule.get("blocking", False):
                entry["blocking"] = True
            if raw_rule.get("contexts"):
                entry["contexts"] = (entry.get("contexts") or []) + raw_rule["contexts"]  # type: ignore[index]
            if raw_rule.get("applies_to"):
                existing_roles = set(entry.get("applies_to") or [])
                for role in raw_rule["applies_to"]:
                    if role:
                        existing_roles.add(role)
                entry["applies_to"] = sorted(existing_roles)
            if raw_rule.get("source") or raw_rule.get("sourcePath"):
                entry["source"] = source_obj

            # Project is authoritative: if it provides guidance/body, override composed body.
            if raw_rule.get("guidance") or raw_rule.get("source") or raw_rule.get("sourcePath"):
                entry["body"] = body
                entry["guidance"] = raw_rule.get("guidance")

            entry.setdefault("origins", []).append("project")
            existing = set(entry.get("dependencies") or [])
            for p in deps:
                existing.add(str(p))
            entry["dependencies"] = sorted(existing)
            entry["_body_resolved"] = bool(entry.get("_body_resolved")) and bool(resolve_sources)

        return {
            "version": core.get("version") or "1.0.0",
            "packs": packs,
            "rules": rules_index,
        }

    def compose_cli_rules(
        self,
        packs: Optional[List[str]] = None,
        *,
        resolve_sources: bool = False,
    ) -> Dict[str, Any]:
        """Compose ONLY rules that define `cli` display configuration.

        This is a performance-oriented subset used for CLI before/after guidance.
        """
        packs = list(packs or [])

        core = self.load_core_registry()
        rules_index: Dict[str, Dict[str, Any]] = {}

        def _has_cli(rule_dict: Dict[str, Any]) -> bool:
            cli_cfg = rule_dict.get("cli") or {}
            if not isinstance(cli_cfg, dict):
                return False
            cmds = cli_cfg.get("commands") or []
            return isinstance(cmds, list) and len(cmds) > 0

        # Core rules with cli first
        for raw_rule in core.get("rules", []) or []:
            if not isinstance(raw_rule, dict):
                continue
            if not _has_cli(raw_rule):
                continue
            rid = str(raw_rule.get("id") or "").strip()
            if not rid:
                continue

            body, deps = self._compose_rule_body(raw_rule, origin="core", packs=packs, resolve_sources=resolve_sources)
            rules_index[rid] = {
                "id": rid,
                "title": raw_rule.get("title") or rid,
                "blocking": bool(raw_rule.get("blocking", False)),
                "body": body,
                "cli": raw_rule.get("cli") or {},
                "origins": ["core"],
                "dependencies": [str(p) for p in deps],
            }

        # Pack overlays: include rules that have cli OR that extend an existing cli rule
        for pack_name in packs:
            pack_registry = self.load_pack_registry(pack_name)
            for raw_rule in pack_registry.get("rules", []) or []:
                if not isinstance(raw_rule, dict):
                    continue
                rid = str(raw_rule.get("id") or "").strip()
                if not rid:
                    continue

                if not _has_cli(raw_rule) and rid not in rules_index:
                    continue

                body, deps = self._compose_rule_body(
                    raw_rule,
                    origin=f"pack:{pack_name}",
                    packs=packs,
                    resolve_sources=resolve_sources,
                )

                if rid not in rules_index:
                    rules_index[rid] = {
                        "id": rid,
                        "title": raw_rule.get("title") or rid,
                        "blocking": bool(raw_rule.get("blocking", False)),
                        "body": body,
                        "cli": raw_rule.get("cli") or {},
                        "origins": [f"pack:{pack_name}"],
                        "dependencies": [str(p) for p in deps],
                    }
                    continue

                entry = rules_index[rid]
                if raw_rule.get("title"):
                    entry["title"] = raw_rule["title"]
                if raw_rule.get("blocking", False):
                    entry["blocking"] = True
                if raw_rule.get("cli"):
                    entry["cli"] = raw_rule.get("cli") or entry.get("cli") or {}
                entry["body"] = (entry.get("body") or "") + (body or "")
                entry.setdefault("origins", []).append(f"pack:{pack_name}")
                existing = set(entry.get("dependencies") or [])
                for p in deps:
                    existing.add(str(p))
                entry["dependencies"] = sorted(existing)

        return {
            "version": core.get("version") or "1.0.0",
            "packs": packs,
            "rules": rules_index,
        }

    def compose_cli_rules_for_command(
        self,
        packs: Optional[List[str]] = None,
        *,
        command_name: str,
        resolve_sources: bool = False,
    ) -> Dict[str, Any]:
        """Compose ONLY CLI rules relevant to a specific command.

        This avoids composing and resolving includes for unrelated rules, which
        improves CLI startup for commands that have no CLI guidance attached.
        """
        packs = list(packs or [])

        core = self.load_core_registry()

        def _cli_commands(rule_dict: Dict[str, Any]) -> List[str]:
            cli_cfg = rule_dict.get("cli") or {}
            if not isinstance(cli_cfg, dict):
                return []
            cmds = cli_cfg.get("commands") or []
            return [str(c) for c in cmds] if isinstance(cmds, list) else []

        # First pass: identify matching rule IDs across core + packs
        matching_ids: Set[str] = set()
        for raw_rule in core.get("rules", []) or []:
            if not isinstance(raw_rule, dict):
                continue
            rid = str(raw_rule.get("id") or "").strip()
            if not rid:
                continue
            cmds = _cli_commands(raw_rule)
            if command_name in cmds or "*" in cmds:
                matching_ids.add(rid)

        for pack_name in packs:
            pack_registry = self.load_pack_registry(pack_name)
            for raw_rule in pack_registry.get("rules", []) or []:
                if not isinstance(raw_rule, dict):
                    continue
                rid = str(raw_rule.get("id") or "").strip()
                if not rid:
                    continue
                cmds = _cli_commands(raw_rule)
                if command_name in cmds or "*" in cmds:
                    matching_ids.add(rid)

        if not matching_ids:
            return {
                "version": core.get("version") or "1.0.0",
                "packs": packs,
                "rules": {},
            }

        rules_index: Dict[str, Dict[str, Any]] = {}

        # Compose core matching rules (only those with CLI config)
        for raw_rule in core.get("rules", []) or []:
            if not isinstance(raw_rule, dict):
                continue
            rid = str(raw_rule.get("id") or "").strip()
            if not rid or rid not in matching_ids:
                continue
            cli_cfg = raw_rule.get("cli") or {}
            if not isinstance(cli_cfg, dict):
                continue
            if not _cli_commands(raw_rule):
                continue

            body, deps = self._compose_rule_body(raw_rule, origin="core", packs=packs, resolve_sources=resolve_sources)
            rules_index[rid] = {
                "id": rid,
                "title": raw_rule.get("title") or rid,
                "blocking": bool(raw_rule.get("blocking", False)),
                "body": body,
                "cli": cli_cfg,
                "origins": ["core"],
                "dependencies": [str(p) for p in deps],
            }

        # Apply pack overlays for matching IDs (allow extending core rule bodies)
        for pack_name in packs:
            pack_registry = self.load_pack_registry(pack_name)
            for raw_rule in pack_registry.get("rules", []) or []:
                if not isinstance(raw_rule, dict):
                    continue
                rid = str(raw_rule.get("id") or "").strip()
                if not rid or rid not in matching_ids:
                    continue

                body, deps = self._compose_rule_body(
                    raw_rule,
                    origin=f"pack:{pack_name}",
                    packs=packs,
                    resolve_sources=resolve_sources,
                )

                if rid not in rules_index:
                    cli_cfg = raw_rule.get("cli") or {}
                    if not isinstance(cli_cfg, dict) or not _cli_commands(raw_rule):
                        # If pack is trying to extend a rule that doesn't exist in core
                        # (and doesn't itself define CLI commands), ignore it.
                        continue
                    rules_index[rid] = {
                        "id": rid,
                        "title": raw_rule.get("title") or rid,
                        "blocking": bool(raw_rule.get("blocking", False)),
                        "body": body,
                        "cli": cli_cfg,
                        "origins": [f"pack:{pack_name}"],
                        "dependencies": [str(p) for p in deps],
                    }
                    continue

                entry = rules_index[rid]
                if raw_rule.get("title"):
                    entry["title"] = raw_rule["title"]
                if raw_rule.get("blocking", False):
                    entry["blocking"] = True
                if raw_rule.get("cli"):
                    entry["cli"] = raw_rule.get("cli") or entry.get("cli") or {}
                entry["body"] = (entry.get("body") or "") + (body or "")
                entry.setdefault("origins", []).append(f"pack:{pack_name}")
                existing = set(entry.get("dependencies") or [])
                for p in deps:
                    existing.add(str(p))
                entry["dependencies"] = sorted(existing)

        return {
            "version": core.get("version") or "1.0.0",
            "packs": packs,
            "rules": rules_index,
        }

    def compose_rule(self, rule_id: str, packs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compose a single rule by ID.

        Returns a dict with the rule metadata and composed content.
        Used by the CLI to show individual rules.
        """
        composed = self.compose(packs=packs)
        rules_dict = composed.get("rules", {})

        if rule_id not in rules_dict:
            raise RulesCompositionError(f"Rule not found: {rule_id}")

        rule = rules_dict[rule_id]

        # Build response with anchor information from source path
        source_path_str = rule.get("source", {}).get("file", "")
        if "#" in source_path_str:
            file_part, anchor_part = source_path_str.split("#", 1)
        else:
            file_part = source_path_str
            anchor_part = ""

        return {
            "id": rule["id"],
            "title": rule.get("title", ""),
            "category": rule.get("category", ""),
            "blocking": rule.get("blocking", False),
            "applies_to": rule.get("applies_to", []) or [],
            "sourcePath": source_path_str,
            "startAnchor": f"<!-- ANCHOR: {anchor_part} -->" if anchor_part else "",
            "endAnchor": f"<!-- END ANCHOR: {anchor_part} -->" if anchor_part else "",
            "content": rule.get("body", ""),
            "guidance": str(rule.get("guidance") or "").strip(),
            "contexts": rule.get("contexts", []),
        }

    def load_composed_rules(self, packs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Load all composed rules as a list.

        Returns a list of rule dicts suitable for filtering and display.
        """
        composed = self.compose(packs=packs)
        rules_dict = composed.get("rules", {})

        # Convert to list format
        rules_list = []
        for rule_id, rule in rules_dict.items():
            source_path_str = rule.get("source", {}).get("file", "")
            rules_list.append({
                "id": rule["id"],
                "title": rule.get("title", ""),
                "category": rule.get("category", ""),
                "blocking": rule.get("blocking", False),
                "applies_to": rule.get("applies_to", []) or [],
                "sourcePath": source_path_str,
                "content": rule.get("body", ""),
                "guidance": str(rule.get("guidance") or "").strip(),
                "contexts": rule.get("contexts", []),
            })

        return rules_list


def compose_rules(packs: Optional[List[str]] = None, project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience wrapper for composing rules via RulesRegistry.

    Used by tests and CLI entrypoints.

    Args:
        packs: List of pack names to include (optional)
        project_root: Project root path (optional, defaults to PathResolver.resolve_project_root())
    """
    registry = RulesRegistry(project_root=project_root)
    return registry.compose(packs=packs)


# ------------------------------------------------------------------
# Role-based rule query API (uses composition system)
# ------------------------------------------------------------------
def get_rules_for_role(role: str, packs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get composed rules that apply to a specific role.

    Uses RulesRegistry.compose() to get fully composed rules with:
    - Pack overlays
    - Project overlays
    - Include resolution

    Args:
        role: One of 'orchestrator', 'agent', 'validator'
        packs: Optional list of active packs (defaults to empty)

    Returns:
        List of composed rule dictionaries where applies_to includes the role

    Raises:
        ValueError: If role is not one of the valid options
    """
    if role not in ('orchestrator', 'agent', 'validator'):
        raise ValueError(f"Invalid role: {role}. Must be orchestrator, agent, or validator")

    # Use composition system for full rule resolution
    registry = RulesRegistry()
    composed = registry.compose(packs=packs or [])
    rules_map = composed.get("rules", {})
    
    # Filter by role from composed rules
    return [
        rule for rule in rules_map.values()
        if role in (rule.get('applies_to') or [])
    ]


def filter_rules(context: Dict[str, Any], packs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Filter composed rules by context metadata (role, category, etc.).

    Uses RulesRegistry.compose() for full rule resolution.

    Args:
        context: Dictionary with optional keys:
            - role: One of 'orchestrator', 'agent', 'validator'
            - category: Rule category (e.g., 'validation', 'delegation')
        packs: Optional list of active packs (defaults to empty)

    Returns:
        List of composed rule dictionaries matching the context filters
    """
    # Use composition system for full rule resolution
    registry = RulesRegistry()
    composed = registry.compose(packs=packs or [])
    rules = list(composed.get("rules", {}).values())

    # Filter by role if specified
    if 'role' in context:
        rules = [r for r in rules if context['role'] in (r.get('applies_to') or [])]

    # Filter by category if specified
    if 'category' in context:
        rules = [r for r in rules if r.get('category') == context['category']]

    return rules


__all__ = [
    "RulesRegistry",
    "compose_rules",
    "get_rules_for_role",
    "filter_rules",
]
