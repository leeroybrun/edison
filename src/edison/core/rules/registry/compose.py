"""Rule composition helpers for the rules registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from edison.core.composition.core.errors import AnchorNotFoundError, RulesCompositionError
from edison.core.composition.core.sections import SectionParser
from edison.core.utils.profiling import span

from .rule_body import RulesRegistryRuleBodyMixin


class RulesRegistryComposeMixin(RulesRegistryRuleBodyMixin):
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

        def _apply_overlay_layer(layer_id: str, layer_root: Path, *, authoritative: bool) -> None:
            with span("rules.compose.layer", layer=layer_id, authoritative=authoritative):
                registry = self._load_yaml(layer_root / "rules" / "registry.yml", required=False)

            for raw_rule in registry.get("rules", []) or []:
                if not isinstance(raw_rule, dict):
                    continue
                rid = str(raw_rule.get("id") or "").strip()
                if not rid:
                    continue

                with span("rules.compose.rule", origin=layer_id, id=rid):
                    body, deps = self._compose_rule_body(
                        raw_rule,
                        origin=layer_id,
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
                        "origins": [layer_id],
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

                if authoritative and (
                    raw_rule.get("guidance") or raw_rule.get("source") or raw_rule.get("sourcePath")
                ):
                    # Highest-precedence layer is authoritative: if it provides guidance/body, override.
                    entry["body"] = body
                    entry["guidance"] = raw_rule.get("guidance")
                else:
                    # Non-final layers append guidance/body.
                    entry["body"] = (entry.get("body") or "") + (body or "")
                    if raw_rule.get("guidance"):
                        prior = (entry.get("guidance") or "")
                        if prior:
                            entry["guidance"] = str(prior).rstrip() + "\n" + str(raw_rule["guidance"]).rstrip()
                        else:
                            entry["guidance"] = raw_rule["guidance"]

                entry.setdefault("origins", []).append(layer_id)
                existing_deps = set(entry.get("dependencies") or [])
                for p in deps:
                    existing_deps.add(str(p))
                entry["dependencies"] = sorted(existing_deps)
                entry["_body_resolved"] = bool(entry.get("_body_resolved")) and bool(resolve_sources)

        # Overlay layers (e.g., company → user → project). Highest-precedence layer is authoritative.
        for idx, (layer_id, layer_root) in enumerate(self._overlay_layers):
            _apply_overlay_layer(
                layer_id,
                layer_root,
                authoritative=(idx == len(self._overlay_layers) - 1),
            )

        return {
            "version": core.get("version") or "1.0.0",
            "packs": packs,
            "rules": rules_index,
        }
