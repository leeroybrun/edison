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
from typing import Optional

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
        )

        # Persist task
        self.task_repo.save(task)

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

    def claim_task(self, task_id: str, session_id: str) -> Task:
        """Claim a task for a session (todo -> wip transition).

        This workflow operation:
        1. Validates transition using unified StateValidator (enforcing guards)
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
        from edison.core.state.transitions import validate_transition

        # 1. Load task
        task = self.task_repo.get(task_id)
        if not task:
            raise PersistenceError(f"Task not found: {task_id}")

        workflow_config = WorkflowConfig()
        wip_state = workflow_config.get_semantic_state("task", "wip")

        # Build context for guards
        context = {
            "task": task.to_dict(),
            "session": {"id": session_id},
            # Simulate session assignment for the guard check 'task_claimed'
            # The guard might check if task.session_id matches session.id
            # We haven't assigned it yet, so we pass it in context
            "proposed_session_id": session_id,
        }
        # Update task context to appear claimed for the check if needed, 
        # OR rely on 'can_start_task' guard which checks if task is claimed.
        # Actually, 'can_start_task' guard checks if task is claimed by current session.
        # Since we are *performing* the claim, we are transitioning TO wip.
        # The guard `can_start_task` usually runs on todo->wip. 
        # Let's check `data/guards/task.py`: `can_start_task` checks `task_session == session_id`.
        # Since we haven't saved the session_id to the task yet, the guard might fail if we strictly use the current task state.
        # However, `claim_task` IS the action of claiming. 
        # We should probably update the task object in memory first, then validate.
        
        task.session_id = session_id
        context["task"]["session_id"] = session_id # Update context to reflect proposed state

        # Validate transition
        valid, reason = validate_transition(
            "task", 
            task.state, 
            wip_state, 
            context=context
        )
        if not valid:
            raise PersistenceError(f"Cannot claim task {task_id}: {reason}")

        # 2. Update task entity
        from edison.core.utils.time import utc_timestamp
        now = utc_timestamp()
        
        old_state = task.state
        task.state = wip_state
        # task.session_id already set above
        task.claimed_at = task.claimed_at or now
        task.last_active = now
        task.record_transition(old_state, wip_state, reason="claimed")

        # 3. Save (handles move)
        self.task_repo.save(task)

        # 4. Register task in session
        from edison.core.session.persistence.graph import register_task
        register_task(
            session_id,
            task_id,
            owner=task.metadata.created_by or "_unassigned_",
            status=wip_state,
        )

        # 5. Move QA file
        self._move_qa_to_session(task_id, session_id)

        return task

    def complete_task(self, task_id: str, session_id: str) -> Task:
        """Complete a task (wip -> done transition).

        This workflow operation:
        1. Validates transition using unified StateValidator (enforcing guards like can_finish_task)
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
        from edison.core.state.transitions import validate_transition

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

        # Validate transition
        # Context needs task data for guards like 'can_finish_task' (checks implementation report)
        context = {
            "task": task.to_dict(),
            "session": {"id": session_id},
        }
        
        valid, reason = validate_transition(
            "task", 
            task.state, 
            done_state, 
            context=context
        )
        if not valid:
            raise PersistenceError(f"Cannot complete task {task_id}: {reason}")

        # 2. Update task entity
        from edison.core.utils.time import utc_timestamp
        now = utc_timestamp()
        
        old_state = task.state
        task.state = done_state
        task.last_active = now
        task.record_transition(old_state, done_state, reason="completed")

        # 3. Save (handles move)
        self.task_repo.save(task)

        # 4. Update task status in session
        from edison.core.session.persistence.graph import update_record_status
        update_record_status(session_id, task_id, "task", done_state)

        # 5. Advance QA
        self._advance_qa_for_completion(task_id, session_id)

        return task

    # ---------- Internal Helpers ----------

    def _create_qa_for_task(self, task: Task) -> None:
        """Create QA record for a task.

        Args:
            task: Task entity
        """
        from edison.core.qa.models import QARecord
        from edison.core.config.domains.workflow import WorkflowConfig

        qa_id = f"{task.id}-qa"

        # Don't recreate if already exists
        if self.qa_repo.exists(qa_id):
            return

        waiting_state = WorkflowConfig().get_semantic_state("qa", "waiting")

        qa = QARecord(
            id=qa_id,
            task_id=task.id,
            state=waiting_state,
            title=f"QA for {task.id}: {task.title}",
            session_id=task.session_id,
            metadata=EntityMetadata.create(
                created_by=task.metadata.created_by,
                session_id=task.session_id,
            ),
        )

        self.qa_repo.save(qa)

        # Register QA in session if task has session_id
        if task.session_id:
            from edison.core.session.persistence.graph import register_qa
            register_qa(
                task.session_id,
                task.id,
                qa_id,
                status=waiting_state,
                round_no=1,
            )

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

            # Update QA status in session
            from edison.core.session.persistence.graph import update_record_status
            update_record_status(session_id, qa_id, "qa", todo_state)


__all__ = ["TaskQAWorkflow"]
