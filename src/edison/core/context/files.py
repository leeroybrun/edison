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
        self._ignore_patterns: Optional[list[str]] = None

    @property
    def project_root(self) -> Path:
        """Get project root, resolving lazily if needed."""
        if self._project_root is None:
            self._project_root = PathResolver.resolve_project_root()
        return self._project_root

    def _get_ignore_patterns(self) -> list[str]:
        """Return glob patterns to ignore for file-context detection.

        This is primarily used to prevent Edison-managed metadata/runtime artifacts
        (e.g., `.project/**`) from polluting validation "modifiedFiles" and triggering
        irrelevant validators.
        """
        if self._ignore_patterns is not None:
            return self._ignore_patterns

        patterns: list[str] = []
        try:
            from edison.core.config.domains.qa import QAConfig

            validation_cfg = QAConfig(repo_root=self.project_root).get_validation_config()
            file_ctx_cfg = validation_cfg.get("fileContext", {}) or {}
            if isinstance(file_ctx_cfg, dict):
                raw = (
                    file_ctx_cfg.get("ignorePatterns")
                    or file_ctx_cfg.get("ignore")
                    or []
                )
                if isinstance(raw, list):
                    for item in raw:
                        s = str(item).strip()
                        if s:
                            patterns.append(s)
        except Exception:
            patterns = []

        self._ignore_patterns = patterns
        return patterns

    def _normalize_path(self, raw: str) -> str:
        p = (raw or "").strip()
        if not p:
            return ""
        if p.startswith("./"):
            p = p[2:]

        # Prefer repo-root relative paths for pattern matching.
        try:
            candidate = Path(p)
            if candidate.is_absolute():
                try:
                    p = str(candidate.resolve().relative_to(self.project_root.resolve()))
                except Exception:
                    p = str(candidate)
        except Exception:
            pass

        # Normalize separators for pattern matching.
        try:
            return str(Path(p).as_posix())
        except Exception:
            return p.replace("\\", "/")

    def _filter_files(self, files: list[str]) -> list[str]:
        """Filter out ignored files while preserving order."""
        if not files:
            return []

        ignore = self._get_ignore_patterns()
        if not ignore:
            return [self._normalize_path(f) for f in files if self._normalize_path(f)]

        from edison.core.utils.patterns import matches_any_pattern

        out: list[str] = []
        for raw in files:
            norm = self._normalize_path(str(raw))
            if not norm:
                continue
            if matches_any_pattern(norm, ignore):
                continue
            out.append(norm)
        return out

    def _dedupe_preserve(self, files: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for f in files:
            if f and f not in seen:
                seen.add(f)
                out.append(f)
        return out

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

        modified = self._filter_files(status.get("modified", []))
        staged = self._filter_files(status.get("staged", []))
        untracked = self._filter_files(status.get("untracked", []))
        all_files = self._dedupe_preserve(modified + staged + untracked)

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
                files = self._filter_files(self._extract_files_from_report(report))
                if not files:
                    try:
                        round_dir = evidence.ensure_round()
                        report_path = round_dir / evidence.implementation_filename
                        files = self._filter_files(self._extract_files_from_report_body(report_path))
                    except Exception:
                        files = []
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

        Uses git diff against the session's base branch (from session metadata when
        available) and unions that with `git status` for the session worktree.

        Args:
            session_id: Session identifier

        Returns:
            FileContext with files changed in the session
        """
        from edison.core.utils.git.diff import get_changed_files

        base_branch = "main"
        base_branch_from_session: Optional[str] = None
        try:
            from edison.core.session.persistence.repository import SessionRepository

            session = SessionRepository(project_root=self.project_root).get(session_id)
            if session and getattr(session, "git", None) is not None:
                base_branch_from_session = getattr(session.git, "base_branch", None)
                if base_branch_from_session:
                    base_branch = base_branch_from_session
        except Exception:
            pass

        # Fall back to configured base branch only when session metadata is unavailable.
        if not base_branch_from_session:
            try:
                from edison.core.config.domains.session import SessionConfig

                cfg = SessionConfig(repo_root=self.project_root).get_worktree_config()
                base_branch = str(cfg.get("baseBranch") or base_branch)
            except Exception:
                pass

        diff_files: list[str] = []
        try:
            changed = get_changed_files(
                self.project_root,
                base_branch=base_branch,
                session_id=session_id,
            )
            diff_files = self._filter_files([str(f) for f in changed])
        except Exception:
            diff_files = []

        # Include uncommitted changes (modified/staged/untracked) from the session worktree.
        status_modified: list[str] = []
        status_staged: list[str] = []
        status_untracked: list[str] = []
        try:
            from edison.core.utils.git.status import get_status

            status = get_status(self.project_root, session_id=session_id)
            status_modified = self._filter_files([str(p) for p in status.get("modified", [])])
            status_staged = self._filter_files([str(p) for p in status.get("staged", [])])
            status_untracked = self._filter_files([str(p) for p in status.get("untracked", [])])
        except Exception:
            pass

        all_files = self._dedupe_preserve(status_modified + status_staged + status_untracked + diff_files)

        return FileContext(
            all_files=all_files,
            modified=[p for p in (status_modified + diff_files) if p],
            created=[p for p in status_untracked if p],
            staged=[p for p in status_staged if p],
            untracked=[p for p in status_untracked if p],
            source="git_diff",
        )

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

    def _extract_files_from_report_body(self, report_path: Path) -> list[str]:
        """Extract changed files from the Markdown body when frontmatter omits file lists."""
        try:
            from edison.core.utils.io import read_text
            from edison.core.utils.text import parse_frontmatter

            doc = parse_frontmatter(read_text(report_path))
            body = doc.content or ""
        except Exception:
            return []

        in_changed_section = False
        files: list[str] = []
        seen: set[str] = set()

        for raw in body.splitlines():
            line = raw.rstrip("\n")
            stripped = line.strip()
            if stripped.startswith("## "):
                header = stripped[3:].strip().lower()
                in_changed_section = header in {"changed files", "changed file", "files changed", "files"}
                continue

            if not in_changed_section:
                continue

            if not stripped.startswith("-"):
                continue

            item = stripped.lstrip("-").strip()
            if item.startswith("`") and item.endswith("`") and len(item) >= 2:
                item = item[1:-1].strip()
            if not item or " " in item:
                continue

            if item not in seen:
                seen.add(item)
                files.append(item)

        return files


__all__ = ["FileContext", "FileContextService"]
