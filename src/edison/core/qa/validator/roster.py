from __future__ import annotations
import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional
from edison.core.task import TaskRepository
from ...session.lifecycle import manager as session_manager
from edison.core.config.domains.qa import QAConfig
from edison.core.utils.subprocess import run_with_timeout
from edison.core.qa._utils import parse_primary_files

__all__ = ["build_validator_roster", "_detect_validators_from_git_diff", "_files_for_task", "_task_type_from_doc"]

def _task_type_from_doc(text: str) -> Optional[str]:
    for line in text.splitlines():
        if "Task Type:" in line:
            return line.split(":", 1)[1].strip().split()[0].lower()
    return None

def _files_for_task(task_id: str) -> List[str]:
    """Extract primary files from a task by ID.

    This function finds the task file, reads its content, and extracts
    the primary files using the shared parse_primary_files() utility.
    """
    try:
        task_repo = TaskRepository()
        p = task_repo.get_path(task_id)
        txt = p.read_text(errors="ignore")
    except FileNotFoundError:
        return []

    return parse_primary_files(txt)

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
        result = run_with_timeout(["git", "diff", "--name-only", f"{base_branch}...HEAD"], cwd=worktree_path, capture_output=True, text=True, check=True)
        changed_files = result.stdout.strip().splitlines()
    except Exception:
        return []
    if not changed_files:
        return []
    qa_config = QAConfig()
    roster = qa_config.validation_config.get("roster") if isinstance(qa_config.validation_config.get("roster"), dict) else {}
    triggered: List[str] = []
    
    # Check all tiers (not just specialized) for validators with fileTriggers
    for tier in qa_config.validator_tiers:
        tier_validators = roster.get(tier, []) or []
        for validator in tier_validators:
            for pattern in validator.get("fileTriggers", []) or []:
                if any(fnmatch.fnmatch(f, pattern) for f in changed_files):
                    vid = validator.get("id")
                    if vid and vid not in triggered:
                        triggered.append(vid)
                    break
    return triggered

def _entry(v: Dict[str, Any], *, default_priority: int, blocking: bool, reason: str, detection_method: str | None = None, include_focus: bool = False) -> Dict[str, Any]:
    entry = {
        "id": v["id"], "name": v.get("name", v["id"]), "model": v.get("model"),
        "zenRole": v.get("zenRole") or v.get("role"), "interface": v.get("interface"),
        "priority": v.get("priority", default_priority), "blocking": blocking, "reason": reason,
        "context7Required": v.get("context7Required", False), "context7Packages": v.get("context7Packages", []),
    }
    if include_focus:
        entry["focus"] = v.get("focus", [])
    if detection_method:
        entry["detectionMethod"] = detection_method
    return entry

def build_validator_roster(task_id: str, session_id: Optional[str] = None, *, validators_cfg: Optional[Dict[str, Any]] = None, manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    qa_config = QAConfig()
    raw_cfg = validators_cfg if validators_cfg is not None else qa_config.validation_config
    if not raw_cfg:
        return {"error": "Could not load validator configs"}
    cfg = raw_cfg if isinstance(raw_cfg, dict) else {}
    roster_cfg = cfg.get("roster") if isinstance(cfg.get("roster"), dict) else {}
    
    # Get tiers from config instead of hardcoding
    tiers = qa_config.validator_tiers
    
    git_triggered_ids: List[str] = []
    detection_method = "task-file-patterns"
    if session_id:
        git_triggered_ids = _detect_validators_from_git_diff(session_id)
        if git_triggered_ids:
            detection_method = "git-diff"
    primary_files = _files_for_task(task_id)
    
    # Build always_required from configured "always run" tiers
    always_required: List[Dict[str, Any]] = []
    triggered_tiers: List[str] = []  # Tiers that require file/git matching
    
    for priority, tier in enumerate(tiers, start=1):
        validators = roster_cfg.get(tier, []) or []
        for v in validators:
            if v.get("alwaysRun", False):
                reason = f"{tier.title()} validator (always runs)"
                always_required.append(_entry(v, default_priority=priority, blocking=True, reason=reason, include_focus=True))
            else:
                # Mark this tier as needing trigger-based matching
                if tier not in triggered_tiers:
                    triggered_tiers.append(tier)
    
    triggered_blocking: List[Dict[str, Any]] = []
    triggered_optional: List[Dict[str, Any]] = []
    
    # Process triggered validators from all triggered tiers
    for tier in triggered_tiers:
        tier_priority = tiers.index(tier) + 1 if tier in tiers else 3
        for v in roster_cfg.get(tier, []) or []:
            # Skip validators that are "alwaysRun" - they're already in always_required
            if v.get("alwaysRun", False):
                continue
            matched = bool(git_triggered_ids and v.get("id") in git_triggered_ids)
            matched_files = [] if matched else [f for pattern in v.get("triggers", []) for f in primary_files if fnmatch.fnmatch(f, pattern)]
            if not (matched or matched_files):
                continue
            reason = f"Triggered by git diff (detection: {detection_method})" if matched else "Triggered by task files: " + f"{', '.join(matched_files[:3])}{'...' if len(matched_files) > 3 else ''}"
            info = _entry(v, default_priority=tier_priority, blocking=v.get("blocksOnFail", False), reason=reason, detection_method=detection_method, include_focus=True)
            (triggered_blocking if v.get("blocksOnFail") else triggered_optional).append(info)
    manifest_cap = (manifest.get("orchestration", {}) or {}).get("maxConcurrentAgents") if isinstance(manifest, dict) else None
    max_concurrent = int(manifest_cap) if manifest_cap is not None else QAConfig().get_max_concurrent_validators()
    total_blocking = len(always_required) + len(triggered_blocking)
    decision_points: List[str] = []
    if total_blocking > max_concurrent:
        waves_needed = (total_blocking + max_concurrent - 1) // max_concurrent
        decision_points.append(f"Total blocking validators ({total_blocking}) exceeds concurrency cap ({max_concurrent}). Run in {waves_needed} waves.")
    if triggered_optional:
        decision_points.append(f"{len(triggered_optional)} optional (non-blocking) validators triggered. Consider running them for comprehensive feedback, but they won't block promotion.")
    if not primary_files:
        decision_points.append("Warning: No primary files detected in task. File pattern matching may be incomplete.")
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
