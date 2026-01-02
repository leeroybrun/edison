"""Query helpers for the rules registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from edison.core.composition.core.errors import AnchorNotFoundError, RulesCompositionError
from edison.core.composition.core.sections import SectionParser
from edison.core.utils.profiling import span

from .cli import RulesRegistryCliMixin


class RulesRegistryQueryMixin(RulesRegistryCliMixin):
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

