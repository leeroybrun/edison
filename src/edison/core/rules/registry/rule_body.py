"""Rule body resolution helpers for the rules registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from edison.core.composition.core.errors import AnchorNotFoundError, RulesCompositionError
from edison.core.composition.core.sections import SectionParser
from edison.core.utils.profiling import span



class RulesRegistryRuleBodyMixin:
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
