"""TaskManager facade used by legacy tests."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from edison.core.paths import PathResolver
import edison.core.task as task
from edison.core.task.config import TaskConfig


class TaskManager:
    """Lightweight OO wrapper around task transitions."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()

    def claim_task(self, task_id: str, session_id: str) -> Path:
        """Move a task from global todo into the session wip queue."""
        _, dest = task.claim_task(task_id, session_id)
        return dest

    def transition_task(self, task_id: str, status: str, *, session_id: Optional[str] = None) -> Path:
        """Transition a session-scoped task to a new status directory.

        The status must be allowed by the configured task state machine.
        """
        cfg = TaskConfig(repo_root=self.project_root)
        allowed = {s.lower() for s in cfg.task_states()}
        target = status.lower()
        if target not in allowed:
            raise ValueError(f"Unknown status '{status}'")

        src = task.find_record(task_id, "task", session_id=session_id)
        dest = task.move_to_status(src, "task", target, session_id=session_id)

        # Keep status line in sync for human readability
        try:
            text = dest.read_text(encoding="utf-8")
        except Exception:
            text = ""

        lines = text.splitlines() if text else []
        wrote = False
        for idx, line in enumerate(lines):
            if line.strip().lower().startswith("status:"):
                lines[idx] = f"status: {target}"
                wrote = True
                break
        if not wrote:
            lines.append(f"status: {target}")
        dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return dest


__all__ = ["TaskManager"]
