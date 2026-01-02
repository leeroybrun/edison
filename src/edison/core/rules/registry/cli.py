"""CLI-focused composition helpers for the rules registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from edison.core.composition.core.errors import AnchorNotFoundError, RulesCompositionError
from edison.core.composition.core.sections import SectionParser
from edison.core.utils.profiling import span

from .compose import RulesRegistryComposeMixin


class RulesRegistryCliMixin(RulesRegistryComposeMixin):
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
