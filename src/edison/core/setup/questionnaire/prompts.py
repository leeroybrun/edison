"""User prompting and default value resolution for setup questionnaire."""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import SetupQuestionnaire


def resolve_options(
    questionnaire: "SetupQuestionnaire",
    question: Dict[str, Any],
    resolved: Dict[str, Any]
) -> List[Any]:
    """Resolve dynamic options for a question.

    Args:
        questionnaire: SetupQuestionnaire instance for discovery
        question: Question definition with 'source' field
        resolved: Previously resolved answers

    Returns:
        List of valid options for this question
    """
    source = question.get("source", "static")
    if source == "static":
        return list(question.get("options") or [])
    if source == "discover_packs":
        return questionnaire.discovery.discover_packs()
    if source == "discover_orchestrators":
        return questionnaire.discovery.discover_orchestrators()
    if source == "discover_validators":
        packs = resolved.get("packs") or []
        return questionnaire.discovery.discover_validators(packs)
    if source == "discover_agents":
        packs = resolved.get("packs") or []
        return questionnaire.discovery.discover_agents(packs)
    return []


def resolve_default_value(
    questionnaire: "SetupQuestionnaire",
    question: Dict[str, Any]
) -> Any:
    """Resolve default value for a question, applying template substitutions.

    Args:
        questionnaire: SetupQuestionnaire instance with detected values
        question: Question definition with 'default' field

    Returns:
        Resolved default value
    """
    raw_default = question.get("default")
    if isinstance(raw_default, str):
        return _render_templates(questionnaire.detected, raw_default)
    if isinstance(raw_default, (list, dict)):
        return copy.deepcopy(raw_default)
    return raw_default


def _render_templates(detected: Dict[str, Any], value: str) -> str:
    """Render {{ detected.* }} templates in a string value.

    Args:
        detected: Dictionary of detected values
        value: Template string with {{ detected.key }} patterns

    Returns:
        String with templates replaced by detected values
    """
    pattern = re.compile(r"\{\{\s*detected\.([a-zA-Z0-9_]+)\s*\}\}")

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(detected.get(key, ""))

    return pattern.sub(_replace, value)


def prompt_user(question: Dict[str, Any], options: List[Any], default: Any) -> Any:
    """Prompt user for input and return their answer.

    Args:
        question: Question definition with 'prompt', 'type' fields
        options: Valid options (for display only)
        default: Default value to show in prompt

    Returns:
        User's answer, with type-specific parsing applied
    """
    prompt = question.get("prompt", question.get("id", ""))
    suffix = f" [{default}]" if default not in (None, "") else ""
    raw = input(f"{prompt}{suffix}: ")
    if raw == "" and default is not None:
        return default
    if question.get("type") == "multiselect":
        return [part.strip() for part in raw.split(",") if part.strip()]
    if question.get("type") == "list":
        return [part.strip() for part in raw.split(",") if part.strip()]
    if question.get("type") == "boolean":
        return raw.lower() in ("y", "yes", "true", "1")
    if question.get("type") == "integer":
        return int(raw)
    return raw
