"""Rule expansion and lookup for session next computation.

Functions for looking up and expanding rules from the registry.
"""
from __future__ import annotations

from typing import Any, Dict, List

from edison.core.utils.git import get_repo_root
from edison.core.io.utils import read_json_safe as io_read_json_safe
from edison.core.session.next.utils import project_cfg_dir


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

REPO_ROOT = get_repo_root()


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
    """Expand rule IDs to full rule objects with content."""
    if not rule_ids:
        return []
    reg_path = project_cfg_dir() / "rules" / "registry.json"
    try:
        registry = io_read_json_safe(reg_path)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for rid in rule_ids:
        entry = next((r for r in registry.get("rules", []) if r.get("id") == rid), None)
        if not entry:
            continue
        src = REPO_ROOT / entry["sourcePath"]
        start = entry.get("start") or f"<!-- RULE: {rid} START -->"
        end = entry.get("end") or f"<!-- RULE: {rid} END -->"
        try:
            lines = src.read_text().splitlines()
            s = next(i for i,l in enumerate(lines) if start in l) + 1
            e = next(i for i in range(s, len(lines)) if end in lines[i])
            content = "\n".join(lines[s:e]).rstrip()
        except Exception:
            content = ""
        out.append({
            "id": rid,
            "title": entry.get("title", rid),
            "sourcePath": entry.get("sourcePath"),
            "content": content,
        })
    return out
