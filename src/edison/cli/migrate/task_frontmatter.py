"""
Edison migration: Convert task/QA files from HTML comments to YAML frontmatter.

This migration script:
1. Finds all task and QA files in .project/tasks/ and .project/qa/
2. Parses existing HTML comment metadata
3. Converts to YAML frontmatter format
4. Optionally merges data from session JSON files (if available)
5. Writes the updated files

SUMMARY: Migrate task/QA files from HTML comments to YAML frontmatter
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.utils.text import parse_html_comment, parse_title, format_frontmatter, has_frontmatter
from edison.core.utils.time import utc_timestamp

SUMMARY = "Migrate task/QA files from HTML comments to YAML frontmatter"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--tasks-only",
        action="store_true",
        help="Only migrate task files",
    )
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Only migrate QA files",
    )
    parser.add_argument(
        "--merge-session",
        action="store_true",
        help="Merge data from session JSON files into task/QA files",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup files before migration (default: True)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup files",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _parse_legacy_task(content: str, path: Path) -> Dict[str, Any]:
    """Parse legacy task file with HTML comments.
    
    Returns dict with all extracted metadata.
    """
    metadata: Dict[str, Any] = {}
    title = ""
    description_lines: List[str] = []
    in_description = False
    
    for line in content.split("\n"):
        if parsed := parse_html_comment(line, "Owner"):
            metadata["owner"] = parsed
        elif parsed := parse_html_comment(line, "Status"):
            # Don't store status - it's derived from directory
            pass
        elif parsed := parse_html_comment(line, "Session"):
            metadata["session_id"] = parsed
        elif not title and (parsed := parse_title(line)):
            title = parsed
            in_description = True
        elif in_description:
            description_lines.append(line)
    
    # Derive state from directory
    metadata["state"] = path.parent.name
    metadata["title"] = title
    metadata["description"] = "\n".join(description_lines).strip()
    
    # Add timestamps if missing
    now = utc_timestamp()
    metadata.setdefault("created_at", now)
    metadata.setdefault("updated_at", now)
    
    return metadata


def _parse_legacy_qa(content: str, path: Path) -> Dict[str, Any]:
    """Parse legacy QA file with HTML comments.
    
    Returns dict with all extracted metadata.
    """
    metadata: Dict[str, Any] = {}
    title = ""
    
    for line in content.split("\n"):
        if parsed := parse_html_comment(line, "Task"):
            metadata["task_id"] = parsed
        elif parsed := parse_html_comment(line, "Status"):
            # Don't store status - it's derived from directory
            pass
        elif parsed := parse_html_comment(line, "Session"):
            metadata["session_id"] = parsed
        elif parsed := parse_html_comment(line, "Round"):
            try:
                metadata["round"] = int(parsed)
            except ValueError:
                metadata["round"] = 1
        elif parsed := parse_html_comment(line, "Validator"):
            metadata["validator_owner"] = parsed
        elif parsed := parse_html_comment(line, "CreatedAt"):
            metadata["created_at"] = parsed
        elif parsed := parse_html_comment(line, "UpdatedAt"):
            metadata["updated_at"] = parsed
        elif parsed := parse_html_comment(line, "StateHistory"):
            try:
                metadata["state_history"] = json.loads(parsed)
            except (ValueError, json.JSONDecodeError):
                pass
        elif not title and (parsed := parse_title(line)):
            title = parsed
    
    # Derive state from directory
    metadata["state"] = path.parent.name
    metadata["title"] = title
    
    # Add timestamps if missing
    now = utc_timestamp()
    metadata.setdefault("created_at", now)
    metadata.setdefault("updated_at", now)
    metadata.setdefault("round", 1)
    
    return metadata


def _convert_task_to_frontmatter(
    content: str, 
    path: Path, 
    session_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Convert task file to YAML frontmatter format.
    
    Args:
        content: Original file content
        path: Path to file (for state derivation)
        session_data: Optional session JSON data for merging
        
    Returns:
        Converted content with YAML frontmatter
    """
    if has_frontmatter(content):
        # Already has frontmatter - skip
        return content
    
    metadata = _parse_legacy_task(content, path)
    task_id = path.stem
    
    # Merge session data if available
    if session_data:
        task_entry = session_data.get("tasks", {}).get(task_id, {})
        if task_entry:
            metadata.setdefault("parent_id", task_entry.get("parentId"))
            metadata.setdefault("child_ids", task_entry.get("childIds", []))
            metadata.setdefault("claimed_at", task_entry.get("claimedAt"))
            metadata.setdefault("last_active", task_entry.get("lastActive"))
    
    # Build frontmatter data
    frontmatter_data: Dict[str, Any] = {
        "id": task_id,
        "title": metadata.get("title", ""),
        "owner": metadata.get("owner"),
        "session_id": metadata.get("session_id"),
        "parent_id": metadata.get("parent_id"),
        "child_ids": metadata.get("child_ids") if metadata.get("child_ids") else None,
        "depends_on": metadata.get("depends_on") if metadata.get("depends_on") else None,
        "blocks_tasks": metadata.get("blocks_tasks") if metadata.get("blocks_tasks") else None,
        "claimed_at": metadata.get("claimed_at"),
        "last_active": metadata.get("last_active"),
        "continuation_id": metadata.get("continuation_id"),
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
    }
    
    # Build new content
    yaml_header = format_frontmatter(frontmatter_data, exclude_none=True)
    
    body_lines = [
        f"# {metadata.get('title', 'Untitled Task')}",
        "",
    ]
    if metadata.get("description"):
        body_lines.append(metadata["description"])
    
    return yaml_header + "\n".join(body_lines)


def _convert_qa_to_frontmatter(
    content: str, 
    path: Path, 
    session_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Convert QA file to YAML frontmatter format.
    
    Args:
        content: Original file content
        path: Path to file (for state derivation)
        session_data: Optional session JSON data for merging
        
    Returns:
        Converted content with YAML frontmatter
    """
    if has_frontmatter(content):
        # Already has frontmatter - skip
        return content
    
    metadata = _parse_legacy_qa(content, path)
    qa_id = path.stem
    
    # Merge session data if available
    if session_data:
        qa_entry = session_data.get("qa", {}).get(qa_id, {})
        if qa_entry:
            metadata.setdefault("evidence", qa_entry.get("evidence", []))
            metadata.setdefault("validators", qa_entry.get("validators", []))
    
    # Build frontmatter data
    frontmatter_data: Dict[str, Any] = {
        "id": qa_id,
        "task_id": metadata.get("task_id", ""),
        "title": metadata.get("title", ""),
        "round": metadata.get("round", 1),
        "validator_owner": metadata.get("validator_owner"),
        "session_id": metadata.get("session_id"),
        "validators": metadata.get("validators") if metadata.get("validators") else None,
        "evidence": metadata.get("evidence") if metadata.get("evidence") else None,
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "state_history": metadata.get("state_history") if metadata.get("state_history") else None,
    }
    
    # Build new content
    yaml_header = format_frontmatter(frontmatter_data, exclude_none=True)
    
    body_lines = [
        f"# {metadata.get('title', 'Untitled QA')}",
        "",
    ]
    
    return yaml_header + "\n".join(body_lines)


def _load_session_data(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    """Load all session JSON files and merge their task/QA data.
    
    Returns:
        Dict mapping session_id -> session data
    """
    sessions: Dict[str, Dict[str, Any]] = {}
    sessions_dir = repo_root / ".project" / "sessions"
    
    if not sessions_dir.exists():
        return sessions
    
    for session_file in sessions_dir.rglob("session.json"):
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            session_id = data.get("id")
            if session_id:
                sessions[session_id] = data
        except (json.JSONDecodeError, Exception):
            continue
    
    return sessions


def main(args: argparse.Namespace) -> int:
    """Migrate task/QA files to YAML frontmatter format."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    
    try:
        repo_root = get_repo_root(args)
        project_dir = repo_root / ".project"
        
        if not project_dir.exists():
            formatter.error("No .project directory found", error_code="no_project")
            return 1
        
        # Load session data if merging
        session_data: Dict[str, Dict[str, Any]] = {}
        if getattr(args, "merge_session", False):
            session_data = _load_session_data(repo_root)
            if not args.json:
                formatter.text(f"Loaded {len(session_data)} session files")
        
        results = {
            "tasks_migrated": [],
            "qa_migrated": [],
            "tasks_skipped": [],
            "qa_skipped": [],
            "errors": [],
        }
        
        # Migrate task files
        if not getattr(args, "qa_only", False):
            tasks_dir = project_dir / "tasks"
            if tasks_dir.exists():
                for task_file in tasks_dir.rglob("*.md"):
                    if task_file.name == "TEMPLATE.md":
                        continue
                    
                    try:
                        content = task_file.read_text(encoding="utf-8")
                        
                        if has_frontmatter(content):
                            results["tasks_skipped"].append(str(task_file))
                            continue
                        
                        # Find matching session data
                        task_session_data = None
                        task_id = task_file.stem
                        for sid, sdata in session_data.items():
                            if task_id in sdata.get("tasks", {}):
                                task_session_data = sdata
                                break
                        
                        new_content = _convert_task_to_frontmatter(content, task_file, task_session_data)
                        
                        if args.dry_run:
                            results["tasks_migrated"].append(str(task_file))
                        else:
                            # Create backup if requested
                            if getattr(args, "backup", True) and not getattr(args, "no_backup", False):
                                backup_path = task_file.with_suffix(".md.bak")
                                backup_path.write_text(content, encoding="utf-8")
                            
                            task_file.write_text(new_content, encoding="utf-8")
                            results["tasks_migrated"].append(str(task_file))
                    except Exception as e:
                        results["errors"].append({"file": str(task_file), "error": str(e)})
        
        # Migrate QA files
        if not getattr(args, "tasks_only", False):
            qa_dir = project_dir / "qa"
            if qa_dir.exists():
                for qa_file in qa_dir.rglob("*.md"):
                    if qa_file.name == "TEMPLATE.md":
                        continue
                    
                    try:
                        content = qa_file.read_text(encoding="utf-8")
                        
                        if has_frontmatter(content):
                            results["qa_skipped"].append(str(qa_file))
                            continue
                        
                        # Find matching session data
                        qa_session_data = None
                        qa_id = qa_file.stem
                        for sid, sdata in session_data.items():
                            if qa_id in sdata.get("qa", {}):
                                qa_session_data = sdata
                                break
                        
                        new_content = _convert_qa_to_frontmatter(content, qa_file, qa_session_data)
                        
                        if args.dry_run:
                            results["qa_migrated"].append(str(qa_file))
                        else:
                            # Create backup if requested
                            if getattr(args, "backup", True) and not getattr(args, "no_backup", False):
                                backup_path = qa_file.with_suffix(".md.bak")
                                backup_path.write_text(content, encoding="utf-8")
                            
                            qa_file.write_text(new_content, encoding="utf-8")
                            results["qa_migrated"].append(str(qa_file))
                    except Exception as e:
                        results["errors"].append({"file": str(qa_file), "error": str(e)})
        
        # Also scan session directories for task/QA files
        sessions_dir = project_dir / "sessions"
        if sessions_dir.exists():
            for session_dir in sessions_dir.rglob("tasks"):
                if not session_dir.is_dir():
                    continue
                for task_file in session_dir.rglob("*.md"):
                    if getattr(args, "qa_only", False):
                        continue
                    try:
                        content = task_file.read_text(encoding="utf-8")
                        if has_frontmatter(content):
                            results["tasks_skipped"].append(str(task_file))
                            continue
                        
                        task_session_data = None
                        task_id = task_file.stem
                        for sid, sdata in session_data.items():
                            if task_id in sdata.get("tasks", {}):
                                task_session_data = sdata
                                break
                        
                        new_content = _convert_task_to_frontmatter(content, task_file, task_session_data)
                        
                        if args.dry_run:
                            results["tasks_migrated"].append(str(task_file))
                        else:
                            if getattr(args, "backup", True) and not getattr(args, "no_backup", False):
                                backup_path = task_file.with_suffix(".md.bak")
                                backup_path.write_text(content, encoding="utf-8")
                            task_file.write_text(new_content, encoding="utf-8")
                            results["tasks_migrated"].append(str(task_file))
                    except Exception as e:
                        results["errors"].append({"file": str(task_file), "error": str(e)})
            
            for qa_dir in sessions_dir.rglob("qa"):
                if not qa_dir.is_dir() or qa_dir.name != "qa":
                    continue
                for qa_file in qa_dir.rglob("*.md"):
                    if getattr(args, "tasks_only", False):
                        continue
                    try:
                        content = qa_file.read_text(encoding="utf-8")
                        if has_frontmatter(content):
                            results["qa_skipped"].append(str(qa_file))
                            continue
                        
                        qa_session_data = None
                        qa_id = qa_file.stem
                        for sid, sdata in session_data.items():
                            if qa_id in sdata.get("qa", {}):
                                qa_session_data = sdata
                                break
                        
                        new_content = _convert_qa_to_frontmatter(content, qa_file, qa_session_data)
                        
                        if args.dry_run:
                            results["qa_migrated"].append(str(qa_file))
                        else:
                            if getattr(args, "backup", True) and not getattr(args, "no_backup", False):
                                backup_path = qa_file.with_suffix(".md.bak")
                                backup_path.write_text(content, encoding="utf-8")
                            qa_file.write_text(new_content, encoding="utf-8")
                            results["qa_migrated"].append(str(qa_file))
                    except Exception as e:
                        results["errors"].append({"file": str(qa_file), "error": str(e)})
        
        if args.json:
            formatter.json_output(results)
        else:
            prefix = "[dry-run] Would migrate" if args.dry_run else "Migrated"
            formatter.text(f"{prefix} {len(results['tasks_migrated'])} task files")
            formatter.text(f"{prefix} {len(results['qa_migrated'])} QA files")
            formatter.text(f"Skipped {len(results['tasks_skipped'])} tasks (already have frontmatter)")
            formatter.text(f"Skipped {len(results['qa_skipped'])} QA (already have frontmatter)")
            if results["errors"]:
                formatter.text(f"Errors: {len(results['errors'])}")
                for err in results["errors"]:
                    formatter.text(f"  - {err['file']}: {err['error']}")
        
        return 0 if not results["errors"] else 1
        
    except Exception as e:
        formatter.error(e, error_code="migration_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))

