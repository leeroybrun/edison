"""Task-QA workflow orchestration.

This module provides high-level workflow operations that coordinate
between Task and QA repositories. These operations were extracted from
TaskRepository to follow Single Responsibility Principle.

Workflow operations include:
- create_task: Create task with associated QA record
- claim_task: Claim task for session (todo -> wip)
- complete_task: Complete task (wip -> done)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from edison.core.entity import EntityMetadata, PersistenceError
from edison.core.utils.paths import PathResolver

from .models import Task
from .repository import TaskRepository


class TaskQAWorkflow:
    """Orchestrates workflow operations across Task and QA domains.

    This class coordinates high-level operations that involve both
    Task and QA repositories, keeping each repository focused on
    its single responsibility (persistence).

    Example:
        workflow = TaskQAWorkflow(project_root)
        task = workflow.create_task("T-001", "Implement feature")
        task = workflow.claim_task("T-001", "session-abc")
        task = workflow.complete_task("T-001", "session-abc")
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize workflow orchestrator.

        Args:
            project_root: Project root directory
        """
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._task_repo: Optional[TaskRepository] = None
        self._qa_repo = None  # Lazy import to avoid circular dependency

    @property
    def task_repo(self) -> TaskRepository:
        """Get or create TaskRepository (lazy initialization)."""
        if self._task_repo is None:
            self._task_repo = TaskRepository(self.project_root)
        return self._task_repo

    @property
    def qa_repo(self):
        """Get or create QARepository (lazy initialization)."""
        if self._qa_repo is None:
            from edison.core.qa.workflow.repository import QARepository
            self._qa_repo = QARepository(self.project_root)
        return self._qa_repo

    # ---------- Workflow Operations ----------

    def create_task(
        self,
        task_id: str,
        title: str,
        *,
        description: str = "",
        session_id: Optional[str] = None,
        owner: Optional[str] = None,
        parent_id: Optional[str] = None,
        continuation_id: Optional[str] = None,
        create_qa: bool = True,
    ) -> Task:
        """Create a new task with optional QA record.

        This workflow operation:
        1. Creates task entity in todo state
        2. Persists task file to appropriate directory
        3. Optionally creates associated QA record
        4. Registers task in session (if session_id provided)

        Args:
            task_id: Task identifier
            title: Task title
            description: Task description (optional)
            session_id: Associated session (optional)
            owner: Task owner/creator (optional)
            create_qa: Whether to create associated QA record (default: True)

        Returns:
            Created Task entity

        Raises:
            TaskStateError: If task already exists
        """
        from edison.core.exceptions import TaskStateError
        from edison.core.config.domains.workflow import WorkflowConfig

        # Check if task already exists
        if self.task_repo.exists(task_id):
            raise TaskStateError(f"Task {task_id} already exists")

        # Determine initial state
        todo_state = WorkflowConfig().get_semantic_state("task", "todo")

        # Create task entity
        task = Task.create(
            task_id=task_id,
            title=title,
            description=description,
            session_id=session_id,
            owner=owner,
            state=todo_state,
            parent_id=parent_id,
            continuation_id=continuation_id,
        )

        # Persist task
        self.task_repo.save(task)

        # Persist parent/child links in task frontmatter (single source of truth).
        # When parent_id is provided but the parent does not exist yet, we still
        # record parent_id on the child (so follow-up linking is retained) and
        # skip updating the parent file.
        if parent_id:
            if str(parent_id).strip() == str(task_id).strip():
                raise PersistenceError("Cannot set a task as its own parent")
            parent = self.task_repo.get(parent_id)
            if parent:
                if task_id not in parent.child_ids:
                    parent.child_ids.append(task_id)
                self.task_repo.save(parent)

        # Register task in session if session_id provided
        if session_id:
            from edison.core.session.persistence.graph import register_task
            register_task(
                session_id,
                task_id,
                owner=owner or "_unassigned_",
                status=todo_state,
            )

        # Create associated QA if requested
        if create_qa:
            self._create_qa_for_task(task)

        return task

    def claim_task(self, task_id: str, session_id: str, *, owner: Optional[str] = None) -> Task:
        """Claim a task for a session (todo -> wip transition).

        This workflow operation:
        1. Validates transition and executes actions via repository.transition()
        2. Updates state to wip
        3. Updates session_id
        4. Moves file to session wip directory
        5. Moves associated QA to session directory
        6. Registers task in session

        Args:
            task_id: Task identifier
            session_id: Session claiming the task

        Returns:
            Updated Task entity

        Raises:
            PersistenceError: If task not found or transition blocked
        """
        from edison.core.config.domains.workflow import WorkflowConfig
        from edison.core.session.lifecycle.recovery import is_session_expired
        from edison.core.session.persistence.repository import SessionRepository as _SessionRepository

        sess_repo = _SessionRepository(project_root=self.project_root)
        if not sess_repo.exists(session_id):
            raise PersistenceError(f"Session not found: {session_id}")
        if is_session_expired(session_id, project_root=self.project_root):
            raise PersistenceError(
                f"Session {session_id} is expired; run `edison session cleanup-expired` or create a new session."
            )

        # 1. Load task
        task = self.task_repo.get(task_id)
        if not task:
            raise PersistenceError(f"Task not found: {task_id}")

        # FAIL-CLOSED: prevent claiming a task already owned by another session.
        if task.session_id and str(task.session_id) != str(session_id):
            raise PersistenceError(
                f"Task {task_id} is already claimed by '{task.session_id}' (cannot claim from '{session_id}')"
            )

        workflow_config = WorkflowConfig()
        wip_state = workflow_config.get_semantic_state("task", "wip")

        # Build context for guards - include proposed session_id for guard evaluation.
        task_ctx = task.to_dict()
        task_ctx["session_id"] = session_id
        task_ctx["sessionId"] = session_id
        context = {
            "task": task_ctx,
            "task_id": task_id,
            "session": {"id": session_id},
            "session_id": session_id,
            "entity_type": "task",
            "entity_id": task_id,
        }

        from edison.core.utils.time import utc_timestamp

        def _mutate(t: Task) -> None:
            now = utc_timestamp()
            t.session_id = session_id
            t.claimed_at = t.claimed_at or now
            t.last_active = now
            if owner and not (t.metadata.created_by or "").strip():
                t.metadata.created_by = owner

        # Validate transition, execute actions, record history, and persist.
        try:
            task = self.task_repo.transition(
                task_id,
                wip_state,
                context=context,
                reason="claimed",
                mutate=_mutate,
            )
        except Exception as e:
            raise PersistenceError(f"Cannot claim task {task_id}: {e}") from e

        # 4. Register task in session
        from edison.core.session.persistence.graph import register_task
        register_task(
            session_id,
            task_id,
            owner=task.metadata.created_by or owner or "_unassigned_",
            status=wip_state,
        )

        # 5. Move QA file
        self._move_qa_to_session(task_id, session_id)

        return task

    def complete_task(self, task_id: str, session_id: str) -> Task:
        """Complete a task (wip -> done transition).

        This workflow operation:
        1. Validates transition and executes actions via repository.transition()
        2. Updates state to done
        3. Moves file to session done directory
        4. Updates task status in session
        5. Advances QA state (waiting -> todo)

        Args:
            task_id: Task identifier
            session_id: Session completing the task

        Returns:
            Updated Task entity

        Raises:
            PersistenceError: If task not found or transition blocked
        """
        from edison.core.config.domains.workflow import WorkflowConfig

        # 1. Load task
        task = self.task_repo.get(task_id)
        if not task:
            raise PersistenceError(f"Task not found: {task_id}")

        # Validation: Must belong to session
        if task.session_id and task.session_id != session_id:
            raise PersistenceError(
                f"Task {task_id} is claimed by '{task.session_id}' (cannot complete from '{session_id}')"
            )

        workflow_config = WorkflowConfig()
        done_state = workflow_config.get_semantic_state("task", "done")

        # Load session for Context7 detection (worktree diff) and better guard context.
        session_obj: dict[str, Any] = {"id": session_id}
        try:
            from edison.core.session.persistence.repository import SessionRepository

            sess = SessionRepository(project_root=self.project_root).get(session_id)
            if sess:
                session_obj = sess.to_dict()
        except Exception:
            pass

        # Build context for guards like 'can_finish_task' (checks implementation report)
        context = {
            "task": task.to_dict(),
            "task_id": task_id,
            "session": session_obj,
            "session_id": session_id,
            "project_root": self.project_root,
            # tasks/ready must enforce evidence requirements (command outputs, etc.)
            "enforce_evidence": True,
            "entity_type": "task",
            "entity_id": task_id,
        }
        
        from edison.core.utils.time import utc_timestamp

        def _mutate(t: Task) -> None:
            t.last_active = utc_timestamp()

        try:
            task = self.task_repo.transition(
                task_id,
                done_state,
                context=context,
                reason="completed",
                mutate=_mutate,
            )
        except Exception as e:
            raise PersistenceError(f"Cannot complete task {task_id}: {e}") from e

        # 4. Advance QA
        self._advance_qa_for_completion(task_id, session_id)

        # 5. Update session index (best-effort).
        try:
            from edison.core.session.persistence.graph import register_task

            register_task(
                session_id,
                task_id,
                owner=task.metadata.created_by or "_unassigned_",
                status=done_state,
            )
        except Exception:
            pass

        return task

    # ---------- Internal Helpers ----------

    def _create_qa_for_task(self, task: Task) -> None:
        """Ensure a QA record exists for a task (idempotent)."""
        self.ensure_qa(
            task_id=task.id,
            session_id=task.session_id,
            validator_owner=None,
            created_by=task.metadata.created_by,
            title=f"QA for {task.id}: {task.title}",
        )

    def ensure_qa(
        self,
        *,
        task_id: str,
        session_id: Optional[str] = None,
        validator_owner: Optional[str] = None,
        created_by: Optional[str] = None,
        title: Optional[str] = None,
    ) -> "QARecord":
        """Ensure the associated QA record exists (create if missing).

        Canonical QA records live under `.project/qa/<state>/<task-id>-qa.md`.
        Evidence lives under `.project/qa/validation-evidence/<task-id>/round-N/`.
        """
        from edison.core.qa.models import QARecord
        from edison.core.config.domains.workflow import WorkflowConfig

        task = self.task_repo.get(task_id)
        if not task:
            raise PersistenceError(f"Task not found: {task_id}")

        qa_id = f"{task_id}-qa"

        qa = self.qa_repo.get(qa_id)
        if qa:
            changed = False
            # Reconcile QA readiness: when a task is already done/validated, the QA should
            # not remain stuck in "waiting".
            try:
                cfg = WorkflowConfig()
                qa_waiting = cfg.get_semantic_state("qa", "waiting")
                qa_todo = cfg.get_semantic_state("qa", "todo")
                task_done = cfg.get_semantic_state("task", "done")
                task_validated = cfg.get_semantic_state("task", "validated")
                if qa.state == qa_waiting and task.state in {task_done, task_validated}:
                    qa.state = qa_todo
                    changed = True
            except Exception:
                # Never fail the caller on best-effort state reconciliation.
                pass
            if session_id and qa.session_id != session_id:
                qa.session_id = session_id
                changed = True
            if validator_owner is not None and qa.validator_owner != validator_owner:
                qa.validator_owner = validator_owner
                changed = True
            if title and qa.title != title:
                qa.title = title
                changed = True
            if changed:
                self.qa_repo.save(qa)
            return qa

        cfg = WorkflowConfig()
        qa_waiting = cfg.get_semantic_state("qa", "waiting")
        qa_todo = cfg.get_semantic_state("qa", "todo")
        task_done = cfg.get_semantic_state("task", "done")
        task_validated = cfg.get_semantic_state("task", "validated")

        initial_state = qa_todo if task.state in {task_done, task_validated} else qa_waiting
        resolved_session = session_id or task.session_id

        qa = QARecord(
            id=qa_id,
            task_id=task_id,
            state=initial_state,
            title=title or f"QA for {task_id}: {task.title}",
            session_id=resolved_session,
            validator_owner=validator_owner,
            metadata=EntityMetadata.create(
                created_by=created_by or task.metadata.created_by,
                session_id=resolved_session,
            ),
        )

        self.qa_repo.save(qa)

        if resolved_session:
            from edison.core.session.persistence.graph import register_qa

            register_qa(
                resolved_session,
                task_id,
                qa_id,
                status=initial_state,
                round_no=1,
            )

        return qa

    def _move_qa_to_session(self, task_id: str, session_id: str) -> None:
        """Move associated QA to session."""
        qa_id = f"{task_id}-qa"

        qa = self.qa_repo.get(qa_id)
        if qa:
            qa.session_id = session_id
            self.qa_repo.save(qa)

            # Register QA in session if not already registered
            from edison.core.session.persistence.graph import register_qa
            register_qa(
                session_id,
                task_id,
                qa_id,
                status=qa.state,
                round_no=qa.round,
            )

    def _advance_qa_for_completion(self, task_id: str, session_id: str) -> None:
        """Advance QA state when task is completed."""
        from edison.core.config.domains.workflow import WorkflowConfig

        qa_id = f"{task_id}-qa"

        qa = self.qa_repo.get(qa_id)
        if qa:
            # waiting -> todo
            todo_state = WorkflowConfig().get_semantic_state("qa", "todo")
            self.qa_repo.advance_state(qa_id, todo_state, session_id)


__all__ = ["TaskQAWorkflow"]
