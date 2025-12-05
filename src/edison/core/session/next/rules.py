"""Rule lookup for session next computation.

Delegates to RulesEngine - NO hardcoded rule IDs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get_engine():
    """Get RulesEngine instance (lazy initialization)."""
    from edison.core.rules import RulesEngine
    from edison.core.config import ConfigManager
    cfg = ConfigManager().load_config(validate=False)
    return RulesEngine(cfg)


def rules_for(domain: str, current: str, to: str, state_spec: Dict[str, Any]) -> List[str]:
    """Get rule IDs for a state transition.
    
    First checks state_spec for transition-specific rules, then falls back
    to RulesEngine for dynamic lookup.
    
    Args:
        domain: State machine domain (task, qa, etc.)
        current: Current state
        to: Target state
        state_spec: State machine specification (may contain transition rules)
        
    Returns:
        List of rule IDs applicable to this transition
    """
    # Try state_spec first (for explicit transition rules)
    try:
        domain_spec = state_spec.get(domain, {})
        for tr in domain_spec.get("transitions", {}).get(current, []):
            if tr.get("to") == to:
                rule_ids = tr.get("rules", []) or []
                if rule_ids:
                    return rule_ids
    except Exception:
        pass
    
    # Fall back to RulesEngine dynamic lookup
    try:
        engine = _get_engine()
        rules = engine.get_rules_for_transition(domain, current, to)
        return [r.get("id") for r in rules if r.get("id")]
    except Exception:
        return []


def expand_rules(rule_ids: List[str]) -> List[Dict[str, Any]]:
    """Expand rule IDs to full rule objects.
    
    Delegates to RulesEngine.expand_rule_ids().
    
    Args:
        rule_ids: List of rule IDs to expand
        
    Returns:
        List of rule info dicts with id, title, content, blocking
    """
    if not rule_ids:
        return []
    
    try:
        engine = _get_engine()
        return engine.expand_rule_ids(rule_ids)
    except Exception:
        return []


def get_rules_for_context(context_type: str) -> List[Dict[str, Any]]:
    """Get rules for a context type (guidance, validation, etc.).
    
    Args:
        context_type: Context type to filter by
        
    Returns:
        List of composed rule dicts
    """
    try:
        engine = _get_engine()
        return engine.get_rules_by_context(context_type)
    except Exception:
        return []


def get_rule(rule_id: str) -> Optional[Dict[str, Any]]:
    """Get a single rule by ID.
    
    Args:
        rule_id: Rule identifier
        
    Returns:
        Composed rule dict or None
    """
    try:
        engine = _get_engine()
        return engine.get_rule(rule_id)
    except Exception:
        return None
