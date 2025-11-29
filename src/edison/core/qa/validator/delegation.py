from __future__ import annotations

import fnmatch
from typing import Any, Dict, List, Optional, Tuple

from edison.core.task import TaskRepository
from edison.core.config.domains.qa import QAConfig
from edison.core.qa._utils import parse_primary_files
from .roster import _task_type_from_doc

__all__ = ["simple_delegation_hint", "enhance_delegation_hint"]


def simple_delegation_hint(
    task_id: str,
    *,
    delegation_cfg: Optional[Dict[str, Any]] = None,
    rule_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    cfg = delegation_cfg if delegation_cfg is not None else QAConfig().delegation_config
    if not cfg:
        return None

    try:
        task_repo = TaskRepository()
        task_path = task_repo.get_path(task_id)
        text = task_path.read_text(errors="ignore")
    except FileNotFoundError:
        return None

    fp_rules: Dict[str, Any] = cfg.get("filePatternRules", {})
    tt_rules: Dict[str, Any] = cfg.get("taskTypeRules", {})
    sad: Dict[str, Any] = cfg.get("subAgentDefaults", {})

    selected: Optional[Tuple[str, str]] = None

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
        task_type = _task_type_from_doc(text)
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
    action: Dict[str, Any] = {
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
    basic_hint: Optional[Dict[str, Any]],
    *,
    delegation_cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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

    task_type = _task_type_from_doc(text)
    files = parse_primary_files(text)

    matched_patterns: List[Dict[str, Any]] = []
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

    reasoning: List[str] = []
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
