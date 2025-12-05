"""Task delegation hints for orchestrators.

This module provides functions to suggest which model/role to use for
implementing tasks based on file patterns, task types, and configuration.

Note: This is for TASK delegation (choosing implementers), not validator
delegation. For validator delegation, see core/qa/engines/delegated.py.
"""
from __future__ import annotations

import fnmatch
from typing import Any

from edison.core.task import TaskRepository
from edison.core.config.domains.qa import QAConfig
from edison.core.qa._utils import parse_primary_files

__all__ = ["simple_delegation_hint", "enhance_delegation_hint", "task_type_from_doc"]


def task_type_from_doc(text: str) -> str | None:
    """Extract task type from task document.

    Args:
        text: Task document text

    Returns:
        Task type string or None if not found
    """
    for line in text.splitlines():
        if "Task Type:" in line:
            return line.split(":", 1)[1].strip().split()[0].lower()
    return None


def simple_delegation_hint(
    task_id: str,
    *,
    delegation_cfg: dict[str, Any] | None = None,
    rule_id: str | None = None,
) -> dict[str, Any] | None:
    """Generate a simple delegation hint for a task.

    Uses the priority chain: filePatternRules → taskTypeRules → subAgentDefaults

    Args:
        task_id: Task identifier
        delegation_cfg: Optional delegation config (uses QAConfig if not provided)
        rule_id: Optional rule ID to include in the hint

    Returns:
        Delegation hint dict or None if no match found
    """
    cfg = delegation_cfg if delegation_cfg is not None else QAConfig().delegation_config
    if not cfg:
        return None

    try:
        task_repo = TaskRepository()
        task_path = task_repo.get_path(task_id)
        text = task_path.read_text(errors="ignore")
    except FileNotFoundError:
        return None

    fp_rules: dict[str, Any] = cfg.get("filePatternRules", {})
    tt_rules: dict[str, Any] = cfg.get("taskTypeRules", {})
    sad: dict[str, Any] = cfg.get("subAgentDefaults", {})

    selected: tuple[str, str] | None = None

    primary_files = parse_primary_files(text)
    for pattern, rule in fp_rules.items():
        for f in primary_files:
            if fnmatch.fnmatch(f, pattern):
                model = rule.get("preferredModel")
                role = rule.get("preferredZenRole") or rule.get("zenRole")
                if model and role:
                    selected = (str(model), str(role))
                    break
        if selected:
            break

    if not selected:
        task_type = task_type_from_doc(text)
        if task_type and task_type in tt_rules:
            rule = tt_rules[task_type]
            model = rule.get("preferredModel")
            role = rule.get("preferredZenRole") or rule.get("zenRole")
            if model and role:
                selected = (str(model), str(role))

    if not selected and sad:
        priority = [
            "api-builder",
            "database-architect-prisma",
            "test-engineer",
            "component-builder-nextjs",
            "feature-implementer",
        ]
        for sub in priority:
            if sub in sad:
                model = sad[sub].get("defaultModel")
                role = sad[sub].get("zenRole")
                if model and role:
                    selected = (str(model), str(role))
                    break

    if not selected:
        return None

    model, role = selected
    action: dict[str, Any] = {
        "id": "delegation.plan",
        "entity": "task",
        "recordId": task_id,
        "cmd": ["zen-mcp", "call", model, "--role", role, "--prompt", "…"],
        "rationale": (
            "Delegation chosen via priority chain "
            "(filePatternRules → taskTypeRules → subAgentDefaults)"
        ),
        "blocking": False,
        "model": model,
        "zenRole": role,
    }
    if rule_id:
        action["ruleRef"] = {"id": rule_id}
    return action


def enhance_delegation_hint(
    task_id: str,
    basic_hint: dict[str, Any] | None,
    *,
    delegation_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enhance a delegation hint with detailed reasoning.

    Args:
        task_id: Task identifier
        basic_hint: Basic hint from simple_delegation_hint
        delegation_cfg: Optional delegation config

    Returns:
        Enhanced hint with reasoning and file analysis
    """
    if not basic_hint:
        return {
            "suggested": False,
            "reason": "No clear delegation pattern matched (orchestrator-direct recommended)",
        }

    cfg = delegation_cfg if delegation_cfg is not None else QAConfig().delegation_config

    try:
        task_repo = TaskRepository()
        task_path = task_repo.get_path(task_id)
        text = task_path.read_text(errors="ignore")
    except Exception:
        return basic_hint

    task_type = task_type_from_doc(text)
    files = parse_primary_files(text)

    matched_patterns: list[dict[str, Any]] = []
    fp_rules = cfg.get("filePatternRules", {})
    for pattern, rule in fp_rules.items():
        for f in files:
            if fnmatch.fnmatch(f, pattern):
                matched_patterns.append(
                    {
                        "pattern": pattern,
                        "file": f,
                        "model": rule.get("preferredModel"),
                        "role": rule.get("preferredZenRole") or rule.get("zenRole"),
                    }
                )

    reasoning: list[str] = []
    if matched_patterns:
        first = matched_patterns[0]
        reasoning.append(f"File pattern match: {first['file']} matches {first['pattern']}")
        reasoning.append(
            f"Delegation config recommends: {first.get('model')} "
            f"with role {first.get('role')}"
        )
    elif task_type:
        tt_rules = cfg.get("taskTypeRules", {})
        if task_type in tt_rules:
            rule = tt_rules[task_type]
            reasoning.append(f"Task type '{task_type}' matched")
            reasoning.append(
                "Delegation config recommends: "
                f"{rule.get('preferredModel')} with role "
                f"{rule.get('preferredZenRole') or rule.get('zenRole')}"
            )
    else:
        reasoning.append("No file pattern or task type match; using sub-agent defaults")

    return {
        "suggested": True,
        "model": basic_hint.get("model"),
        "zenRole": basic_hint.get("zenRole"),
        "interface": "clink" if basic_hint.get("model") in ["codex", "gemini"] else "Task",
        "reasoning": reasoning,
        "cmd": basic_hint.get("cmd"),
        "ruleRef": basic_hint.get("ruleRef"),
        "filesAnalyzed": files,
        "taskType": task_type,
    }

