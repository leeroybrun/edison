"""Rule expansion and lookup for session next computation.

Functions for looking up and expanding rules from the registry.
"""
from __future__ import annotations

from typing import Any, Dict, List

from edison.core.utils.git import get_repo_root


RULE_IDS = {
    "validation_first": "RULE.VALIDATION.FIRST",
    "bundle_first": "RULE.VALIDATION.BUNDLE_FIRST",
    "bundle_approved": "RULE.VALIDATION.BUNDLE_APPROVED_MARKER",
    "fail_closed": "RULE.GUARDS.FAIL_CLOSED",
    "link_scope": "RULE.LINK.SESSION_SCOPE_ONLY",
    "context7": "RULE.CONTEXT7.POSTTRAINING_REQUIRED",
    "evidence": "RULE.EVIDENCE.ROUND_COMMANDS_REQUIRED",
    "delegation": "RULE.DELEGATION.PRIORITY_CHAIN",
}


def _get_repo_root():
    """Get repo root lazily to avoid module-level evaluation."""
    return get_repo_root()


def rules_for(domain: str, current: str, to: str, state_spec: Dict[str, Any]) -> List[str]:
    """Look up rules for a state transition."""
    try:
        domain_spec = state_spec.get(domain, {})
        for tr in domain_spec.get("transitions", {}).get(current, []):
            if tr.get("to") == to:
                return tr.get("rules", []) or []
    except Exception:
        pass
    return []


def expand_rules(rule_ids: List[str]) -> List[Dict[str, Any]]:
    """Expand rule IDs to full rule objects with content.
    
    Uses RulesRegistry directly instead of reading from registry.json.
    """
    if not rule_ids:
        return []
    
    # Lazy import to avoid circular dependency
    from edison.core.rules.registry import RulesRegistry
    
    repo_root = _get_repo_root()
    
    try:
        registry = RulesRegistry(project_root=repo_root)
        composed = registry.compose(packs=[])  # Load core rules
        rules_dict = composed.get("rules", {})
    except Exception:
        return []
    
    out: List[Dict[str, Any]] = []
    for rid in rule_ids:
        entry = rules_dict.get(rid)
        if not entry:
            continue
        
        out.append({
            "id": rid,
            "title": entry.get("title", rid),
            "sourcePath": entry.get("source", {}).get("file", ""),
            "content": entry.get("body", ""),
        })
    return out
