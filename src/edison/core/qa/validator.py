"""Validator orchestration helpers split from legacy QA utilities."""
from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..legacy_guard import enforce_no_legacy_project_root
from ..paths.resolver import PathResolver
from .. import task  # type: ignore
from ..session import manager as session_manager
from . import config as qa_config
from edison.core.utils.subprocess import run_with_timeout


enforce_no_legacy_project_root("lib.qa.validator")


def validate_dimension_weights(config: Dict[str, Any]) -> None:
    """Validate that validation.dimensions exist and sum to 100."""
    dims = ((config.get("validation") or {}).get("dimensions") or {})
    if not dims:
        raise ValueError(
            "validation.dimensions missing. Define weights in edison.yaml under\n"
            "validation: dimensions: (must sum to 100)."
        )

    total = 0
    for key, value in dims.items():
        try:
            iv = int(value)
        except Exception:
            raise ValueError(
                f"dimension '{key}' must be an integer, got {value!r}. "
                "Define validation.dimensions in your project overlays "
                "(<project_config_dir>/config/*.yml) or adjust "
                ".edison/core/config/defaults.yaml."
            )
        if iv < 0 or iv > 100:
            raise ValueError(
                f"dimension '{key}' must be between 0 and 100, got {iv}. "
                "Adjust the weight in configuration."
            )
        total += iv

    if total != 100:
        raise ValueError(
            f"dimension weights must sum to 100, got {total}. "
            "Update validation.dimensions so the total equals 100."
        )


def _task_type_from_doc(text: str) -> Optional[str]:
    for line in text.splitlines():
        if "Task Type:" in line:
            return line.split(":", 1)[1].strip().split()[0].lower()
    return None


def _primary_files_from_doc(text: str) -> List[str]:
    capture = False
    files: List[str] = []
    for line in text.splitlines():
        if line.strip().startswith("- **Primary Files"):
            capture = True
            continue
        if capture:
            if line.startswith("## "):
                break
            if line.strip().startswith("-"):
                files.append(line.split("-", 1)[1].strip())
    return files


def _files_for_task(task_id: str) -> List[str]:
    try:
        p = task.find_record(task_id, "task")
        txt = p.read_text(errors="ignore")
    except FileNotFoundError:
        return []
    files: List[str] = []
    capture = False
    for line in txt.splitlines():
        if "Primary Files / Areas" in line:
            capture = True
            parts = line.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                files.extend([f.strip() for f in parts[1].split(",") if f.strip()])
            continue
        if capture:
            if line.startswith("## "):
                break
            if line.strip().startswith("-"):
                files.append(line.split("-", 1)[1].strip())
    return files


def simple_delegation_hint(
    task_id: str,
    *,
    delegation_cfg: Optional[Dict[str, Any]] = None,
    rule_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    cfg = delegation_cfg if delegation_cfg is not None else qa_config.load_delegation_config()
    if not cfg:
        return None

    try:
        task_path = task.find_record(task_id, "task")
        text = task_path.read_text(errors="ignore")
    except FileNotFoundError:
        return None

    fp_rules: Dict[str, Any] = cfg.get("filePatternRules", {})
    tt_rules: Dict[str, Any] = cfg.get("taskTypeRules", {})
    sad: Dict[str, Any] = cfg.get("subAgentDefaults", {})

    selected: Optional[Tuple[str, str]] = None

    primary_files = _primary_files_from_doc(text)
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

    cfg = delegation_cfg if delegation_cfg is not None else qa_config.load_delegation_config()

    try:
        task_path = task.find_record(task_id, "task")
        text = task_path.read_text(errors="ignore")
    except Exception:
        return basic_hint

    task_type = _task_type_from_doc(text)
    files = _primary_files_from_doc(text)

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


def _detect_validators_from_git_diff(session_id: str) -> List[str]:
    try:
        session = session_manager.get_session(session_id)
    except Exception:
        return []

    git_meta = session.get("git", {}) or {}
    worktree_path = git_meta.get("worktreePath")
    base_branch = git_meta.get("baseBranch", "main")

    if not worktree_path or not Path(worktree_path).exists():
        return []

    try:
        result = run_with_timeout(
            ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        changed_files = result.stdout.strip().splitlines()
    except Exception:
        return []

    if not changed_files:
        return []

    cfg = qa_config.load_validation_config()
    roster = cfg.get("roster") if isinstance(cfg.get("roster"), dict) else {}
    specialized = (roster.get("specialized") or []) if isinstance(roster, dict) else []

    triggered: List[str] = []
    for validator in specialized:
        file_triggers = validator.get("fileTriggers", [])
        if not file_triggers:
            continue
        for pattern in file_triggers:
            if any(fnmatch.fnmatch(f, pattern) for f in changed_files):
                vid = validator.get("id")
                if vid and vid not in triggered:
                    triggered.append(vid)
                break
    return triggered


def build_validator_roster(
    task_id: str,
    session_id: Optional[str] = None,
    *,
    validators_cfg: Optional[Dict[str, Any]] = None,
    manifest: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    raw_cfg = validators_cfg if validators_cfg is not None else qa_config.load_validation_config()
    if not raw_cfg:
        return {"error": "Could not load validator configs"}

    cfg = raw_cfg if isinstance(raw_cfg, dict) else {}
    roster_cfg = cfg.get("roster") if isinstance(cfg.get("roster"), dict) else {}

    git_triggered_ids: List[str] = []
    detection_method = "task-file-patterns"
    if session_id:
        git_triggered_ids = _detect_validators_from_git_diff(session_id)
        if git_triggered_ids:
            detection_method = "git-diff"

    primary_files = _files_for_task(task_id)

    always_required: List[Dict[str, Any]] = []
    triggered_blocking: List[Dict[str, Any]] = []
    triggered_optional: List[Dict[str, Any]] = []

    for v in roster_cfg.get("global", []) or []:
        always_required.append(
            {
                "id": v["id"],
                "name": v.get("name", v["id"]),
                "model": v.get("model"),
                "zenRole": v.get("zenRole") or v.get("role"),
                "interface": v.get("interface"),
                "priority": v.get("priority", 1),
                "blocking": True,
                "reason": "Global validator (always runs)",
                "context7Required": v.get("context7Required", False),
                "context7Packages": v.get("context7Packages", []),
            }
        )

    for v in roster_cfg.get("critical", []) or []:
        always_required.append(
            {
                "id": v["id"],
                "name": v.get("name", v["id"]),
                "model": v.get("model"),
                "zenRole": v.get("zenRole") or v.get("role"),
                "interface": v.get("interface"),
                "priority": v.get("priority", 2),
                "blocking": True,
                "reason": "Critical validator (always runs)",
                "focus": v.get("focus", []),
                "context7Required": v.get("context7Required", False),
                "context7Packages": v.get("context7Packages", []),
            }
        )

    for v in roster_cfg.get("specialized", []) or []:
        matched = False
        matched_files: List[str] = []
        reason = ""

        if git_triggered_ids and v.get("id") in git_triggered_ids:
            matched = True
            reason = f"Triggered by git diff (detection: {detection_method})"

        if not matched:
            triggers = v.get("triggers", [])
            for pattern in triggers:
                for f in primary_files:
                    if fnmatch.fnmatch(f, pattern):
                        matched = True
                        matched_files.append(f)

            if matched:
                reason = (
                    "Triggered by task files: "
                    f"{', '.join(matched_files[:3])}"
                    f"{'...' if len(matched_files) > 3 else ''}"
                )

        if matched:
            info = {
                "id": v["id"],
                "name": v.get("name", v["id"]),
                "model": v.get("model"),
                "zenRole": v.get("zenRole") or v.get("role"),
                "interface": v.get("interface"),
                "priority": v.get("priority", 3),
                "blocking": v.get("blocksOnFail", False),
                "reason": reason,
                "detectionMethod": detection_method,
                "focus": v.get("focus", []),
                "context7Required": v.get("context7Required", False),
                "context7Packages": v.get("context7Packages", []),
            }
            if v.get("blocksOnFail"):
                triggered_blocking.append(info)
            else:
                triggered_optional.append(info)

    if isinstance(manifest, dict):
        manifest_cap = (manifest.get("orchestration", {}) or {}).get("maxConcurrentAgents")
        max_concurrent = int(manifest_cap) if manifest_cap is not None else qa_config.max_concurrent_validators()
    else:
        max_concurrent = qa_config.max_concurrent_validators()

    total_blocking = len(always_required) + len(triggered_blocking)

    decision_points: List[str] = []
    if total_blocking > max_concurrent:
        waves_needed = (total_blocking + max_concurrent - 1) // max_concurrent
        decision_points.append(
            f"Total blocking validators ({total_blocking}) exceeds concurrency cap ({max_concurrent}). "
            f"Run in {waves_needed} waves."
        )
    if triggered_optional:
        decision_points.append(
            f"{len(triggered_optional)} optional (non-blocking) validators triggered. "
            "Consider running them for comprehensive feedback, but they won't block promotion."
        )
    if not primary_files:
        decision_points.append(
            "Warning: No primary files detected in task. File pattern matching may be incomplete."
        )

    return {
        "taskId": task_id,
        "primaryFiles": primary_files,
        "detectionMethod": detection_method,
        "alwaysRequired": sorted(always_required, key=lambda x: x["priority"]),
        "triggeredBlocking": sorted(triggered_blocking, key=lambda x: x["priority"]),
        "triggeredOptional": sorted(triggered_optional, key=lambda x: x["priority"]),
        "maxConcurrent": max_concurrent,
        "totalBlocking": total_blocking,
        "decisionPoints": decision_points,
    }


_SAFE_INCLUDE_RE = re.compile(
    r"\{\{\s*safe_include\(\s*(['\"])"  # opening {{ safe_include(' or "
    r"(?P<path>.+?)\1\s*,\s*fallback\s*=\s*(['\"])"  # path and fallback=
    r"(?P<fallback>.*?)\3\s*\)\s*\}\}"  # closing ) }}
)


def _is_safe_path(rel: str) -> bool:
    if not rel:
        return False
    if rel.startswith(("/", "\\")):
        return False
    if ".." in rel:
        return False
    return True


def _resolve_include_path(rel: str) -> Path | None:
    if not _is_safe_path(rel):
        return None
    try:
        repo_root = PathResolver.resolve_project_root()
        p = (repo_root / rel).resolve()
    except Exception:
        return None
    if p == repo_root or repo_root in p.parents:
        return p if p.is_file() else None
    return None


def _read_text_safe(rel: str) -> str:
    path = _resolve_include_path(rel)
    if not path:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def process_validator_template(template_or_text: str, context: Optional[Dict[str, Any]] = None) -> str:
    given = Path(template_or_text)
    text = given.read_text(encoding="utf-8") if (given.exists() and given.is_file()) else template_or_text

    def _render_safe_include(m: re.Match) -> str:
        rel = m.group("path").strip()
        fallback = m.group("fallback")
        content = _read_text_safe(rel)
        return content if content else fallback

    return _SAFE_INCLUDE_RE.sub(_render_safe_include, text)


def run_validator(validator_markdown_path: str, session_id: str, validator_name: str | None = None) -> str:
    validator_name = validator_name or Path(validator_markdown_path).stem
    repo_root = PathResolver.resolve_project_root()
    standard_path = repo_root / ".edison" / "core" / "validators" / "_report-template.md"
    header = (
        standard_path.read_text(encoding="utf-8")
        if standard_path.exists()
        else (
            f"# {{ validator_name }} Validation Report\n\n"
            "## Executive Summary\n\n"
            "## Dimension Scores\n\n"
            "## Findings\n\n"
            "## Validation Pass/Fail\n\n"
        )
    )

    body = process_validator_template(validator_markdown_path, context={
        "session_id": session_id,
        "validator_name": validator_name,
    })

    return f"{header}\n\n---\n\n{body}\n"


__all__ = [
    "validate_dimension_weights",
    "simple_delegation_hint",
    "enhance_delegation_hint",
    "build_validator_roster",
    "process_validator_template",
    "run_validator",
]
