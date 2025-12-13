"""File context service - single source for modified files.

This module provides the FileContextService which is THE single source
of truth for detecting modified files. It unifies file detection from:
- Git status (current working tree)
- Git diff (session worktree vs base branch)
- Implementation reports (task-specific changes)

All file detection logic should use FileContextService instead of
direct git commands or custom implementations.

Example:
    from edison.core.context.files import FileContextService

    svc = FileContextService()
    ctx = svc.get_for_task("T001")
    print(f"Files for validation: {ctx.all_files}")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from edison.core.utils.paths import PathResolver


@dataclass
class FileContext:
    """Container for file change information.

    Provides normalized access to changed files regardless of source.

    Attributes:
        all_files: All changed files (union of modified, created, deleted, staged, untracked)
        modified: Modified existing files
        created: Newly created files
        deleted: Deleted files
        staged: Staged changes
        untracked: Untracked files
        source: Where the information came from ("git_status", "git_diff", "implementation_report")
    """

    all_files: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    source: str = "unknown"

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return len(self.all_files) > 0


class FileContextService:
    """Single source of truth for detecting modified files.

    This service unifies file detection from multiple sources and provides
    a consistent API for getting file changes.

    The priority order for get_for_task is:
    1. Implementation report (if exists, most accurate for the task)
    2. Git diff against base branch (for session worktrees)
    3. Git status (current working tree)

    Example:
        svc = FileContextService()
        ctx = svc.get_for_task("T001")
        print(f"Modified: {ctx.modified}")
        print(f"Source: {ctx.source}")
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize file context service.

        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        self._project_root = project_root

    @property
    def project_root(self) -> Path:
        """Get project root, resolving lazily if needed."""
        if self._project_root is None:
            self._project_root = PathResolver.resolve_project_root()
        return self._project_root

    def get_current(self) -> FileContext:
        """Get current file changes from git status.

        Returns:
            FileContext with current working tree changes
        """
        from edison.core.utils.git.status import get_status

        try:
            status = get_status(self.project_root)
        except Exception:
            return FileContext(source="git_status")

        modified = status.get("modified", [])
        staged = status.get("staged", [])
        untracked = status.get("untracked", [])
        all_files = list(set(modified + staged + untracked))

        return FileContext(
            all_files=all_files,
            modified=modified,
            staged=staged,
            untracked=untracked,
            source="git_status",
        )

    def get_for_task(
        self,
        task_id: str,
        session_id: Optional[str] = None,
    ) -> FileContext:
        """Get files for a task from implementation report or git.

        Sources (in order of preference):
        1. Implementation report (if exists, most accurate for the task)
        2. Git diff against main branch

        Args:
            task_id: Task identifier
            session_id: Optional session ID for worktree lookup

        Returns:
            FileContext with files for the task
        """
        # Try implementation report first (most accurate for the task)
        try:
            from edison.core.qa.evidence import EvidenceService

            evidence = EvidenceService(task_id, project_root=self.project_root)
            report = evidence.read_implementation_report()
            if report:
                files = self._extract_files_from_report(report)
                if files:
                    return FileContext(
                        all_files=files,
                        modified=files,
                        source="implementation_report",
                    )
        except Exception:
            pass

        # Fall back to git diff
        return self.get_for_session(session_id) if session_id else self.get_current()

    def get_for_session(self, session_id: str) -> FileContext:
        """Get files changed in a session worktree.

        Uses git diff against main branch for the session's worktree.

        Args:
            session_id: Session identifier

        Returns:
            FileContext with files changed in the session
        """
        from edison.core.utils.git.diff import get_changed_files

        try:
            changed = get_changed_files(
                self.project_root,
                base_branch="main",
                session_id=session_id,
            )
            files = [str(f) for f in changed]
            return FileContext(
                all_files=files,
                modified=files,
                source="git_diff",
            )
        except Exception:
            return FileContext(source="git_diff")

    def _extract_files_from_report(self, report: dict[str, Any]) -> list[str]:
        """Extract all changed files from implementation report.

        Args:
            report: Implementation report dict

        Returns:
            List of file paths
        """
        files: list[str] = []

        # Support multiple field names from different report formats
        files.extend(report.get("filesModified", []))
        files.extend(report.get("filesCreated", []))
        files.extend(report.get("filesChanged", []))
        files.extend(report.get("primaryFiles", []))

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique.append(f)
        return unique


__all__ = ["FileContext", "FileContextService"]
