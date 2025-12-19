"""QA repository for file-based persistence.

This module provides the QARepository class that implements
the repository pattern for QA record entities.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.data import get_data_path
from edison.core.entity import (
    BaseRepository,
    FileRepositoryMixin,
    SessionScopedMixin,
    EntityId,
    EntityMetadata,
    PersistenceError,
)
from edison.core.utils.paths import PathResolver
from edison.core.utils.text import (
    format_frontmatter,
    has_frontmatter,
    parse_frontmatter,
    parse_title,
    render_template_text,
    strip_frontmatter_block,
)
from edison.core.config.domains import TaskConfig

from ..models import QARecord
from .._utils import get_qa_root_path


class QARepository(
    BaseRepository[QARecord],
    FileRepositoryMixin[QARecord],
    SessionScopedMixin[QARecord],
):
    """File-based repository for QA record entities.

    QA records are stored as Markdown files in state-based directories:
    - <project-management-dir>/qa/waiting/
    - <project-management-dir>/qa/todo/
    - <project-management-dir>/qa/wip/
    - <project-management-dir>/qa/done/
    - <project-management-dir>/qa/validated/

    Supports session-scoped storage via SessionScopedMixin.
    """

    entity_type: str = "qa"
    file_extension: str = ".md"

    # SessionScopedMixin configuration
    record_type: str = "qa"
    record_subdir: str = "qa"

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize repository.

        Args:
            project_root: Project root directory
        """
        super().__init__(project_root)
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = TaskConfig(repo_root=self.project_root)
        self._qa_root = get_qa_root_path(self.project_root)

    # ---------- Path Resolution ----------

    def _get_state_dir(self, state: str) -> Path:
        """Get directory for a QA state."""
        return self._qa_root / state
    
    def _get_states_to_search(self) -> List[str]:
        """Get list of states to search from configuration.

        Returns:
            List of QA state names

        Raises:
            ValueError: If config doesn't provide QA states
        """
        states = self._config.qa_states()
        if not states:
            raise ValueError("Configuration must define QA states (statemachine.qa.states)")
        return states
    
    def _resolve_entity_path(
        self, 
        entity_id: EntityId, 
        state: Optional[str] = None,
    ) -> Path:
        """Resolve path for a QA record file in global directory."""
        filename = self._get_entity_filename(entity_id)
        if state:
            return self._get_state_dir(state) / filename
        return self._get_state_dir("waiting") / filename
    
    def _get_entity_filename(self, entity_id: EntityId) -> str:
        """Generate filename for a QA record."""
        return f"{entity_id}{self.file_extension}"

    def _find_entity_path(self, entity_id: EntityId) -> Optional[Path]:
        """Find path for a QA record, checking global and session directories.

        Uses SessionScopedMixin for unified search across global and session dirs.
        """
        return self._find_entity_path_with_sessions(entity_id)

    def _resolve_session_qa_path(self, qa_id: str, session_id: str, state: str) -> Path:
        """Resolve path for a QA record in a session directory.

        Uses SessionScopedMixin for session path resolution.
        """
        return self._resolve_session_record_path(qa_id, session_id, state)
    
    # ---------- CRUD Implementation ----------
    
    def _do_create(self, entity: QARecord) -> QARecord:
        """Create a new QA record file."""
        if entity.session_id:
            path = self._resolve_session_qa_path(entity.id, entity.session_id, entity.state)
        else:
            path = self._resolve_entity_path(entity.id, entity.state)
            
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self._qa_to_markdown(entity)
        path.write_text(content, encoding="utf-8")
        return entity
    
    def _do_get(self, entity_id: EntityId) -> Optional[QARecord]:
        """Get a QA record by ID."""
        path = self._find_entity_path(entity_id)
        if path is None:
            return None

        # Strict load for direct lookup: if a file exists but is legacy/unparseable,
        # surface an actionable error instead of pretending the QA doesn't exist.
        content = path.read_text(encoding="utf-8", errors="strict")
        if not has_frontmatter(content):
            raise PersistenceError(
                f"QA file at {path} is missing YAML frontmatter. "
                "Restore the file from the composed template (.edison/_generated/documents/QA.md) "
                "or recreate the QA via `edison qa new <task-id>`."
            )

        try:
            return self._parse_qa_markdown(path.stem, content, path)
        except Exception as exc:
            raise PersistenceError(f"Failed to parse QA file at {path}: {exc}") from exc
    
    def _do_save(self, entity: QARecord) -> None:
        """Save a QA record."""
        current_path = self._find_entity_path(entity.id)
        
        if entity.session_id:
            target_path = self._resolve_session_qa_path(entity.id, entity.session_id, entity.state)
        else:
            target_path = self._resolve_entity_path(entity.id, entity.state)
        
        if current_path is None:
            self._do_create(entity)
            return

        # Preserve existing body (QA briefs are human/LLM-edited documents).
        content_existing = current_path.read_text(encoding="utf-8", errors="strict")
        if not has_frontmatter(content_existing):
            raise PersistenceError(
                f"QA file at {current_path} is missing YAML frontmatter. "
                "Restore the file from the composed template or recreate the QA via `edison qa new <task-id>`."
            )
        body = parse_frontmatter(content_existing).content

        cleanup_old = False
        if current_path.resolve() != target_path.resolve():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                current_path.rename(target_path)
            except OSError:
                cleanup_old = True

        target_path.write_text(self._qa_to_markdown(entity, body=body), encoding="utf-8")
        if cleanup_old and current_path.exists():
            current_path.unlink()
    
    def _do_delete(self, entity_id: EntityId) -> bool:
        """Delete a QA record."""
        path = self._find_entity_path(entity_id)
        if path is None:
            return False
        path.unlink()
        return True
    
    def _do_exists(self, entity_id: EntityId) -> bool:
        """Check if a QA record exists."""
        return self._find_entity_path(entity_id) is not None

    # ---------- Workflow Methods ----------

    def advance_state(self, qa_id: str, new_state: str, session_id: Optional[str] = None) -> QARecord:
        """Advance QA record to a new state using proper state machine validation.
        
        This is a HIGH-LEVEL workflow method that moves QA between states.
        Uses repository.transition() to ensure guards and actions are executed.
        
        Args:
            qa_id: QA record identifier
            new_state: Target state (from config)
            session_id: Optional session context to update ownership
            
        Returns:
            Updated QA record
            
        Raises:
            PersistenceError: If QA not found or transition not allowed
        """
        qa = self.get(qa_id)
        if not qa:
            raise PersistenceError(f"QA record not found: {qa_id}")

        context = {
            "qa": {"id": qa_id, "task_id": qa.task_id, "state": qa.state},
            "session": {"id": session_id} if session_id else {},
            "session_id": session_id,
            "entity_type": "qa",
            "entity_id": qa_id,
        }

        def _mutate(q: QARecord) -> None:
            if session_id:
                q.session_id = session_id

        try:
            return self.transition(
                qa_id,
                new_state,
                context=context,
                reason="qa.advance_state",
                mutate=_mutate,
            )
        except Exception as e:
            raise PersistenceError(f"Transition not allowed: {e}") from e
    
    # ---------- Query Implementation ----------

    def _do_list_by_state(self, state: str) -> List[QARecord]:
        """List QA records in a given state (global + session directories)."""
        records: List[QARecord] = []

        # 1) Global QA directory
        state_dir = self._get_state_dir(state)
        if state_dir.exists():
            for path in state_dir.glob(f"*{self.file_extension}"):
                qa = self._load_qa_from_file(path)
                if qa:
                    records.append(qa)

        # 2) Session QA directories
        for base in self._get_session_bases():
            session_state_dir = base / self.record_subdir / state
            if not session_state_dir.exists():
                continue
            for path in session_state_dir.glob(f"*{self.file_extension}"):
                qa = self._load_qa_from_file(path)
                if qa:
                    records.append(qa)

        return records
    
    def _do_list_all(self) -> List[QARecord]:
        """List all QA records."""
        records: List[QARecord] = []
        for state in self._get_states_to_search():
            records.extend(self._do_list_by_state(state))
        return records
    
    # ---------- QA-specific Methods ----------
    
    def find_by_task(self, task_id: str) -> List[QARecord]:
        """Find QA records for a task."""
        return self._do_find(task_id=task_id)
    
    def find_by_session(self, session_id: str) -> List[QARecord]:
        """Find QA records belonging to a session."""
        return self._do_find(session_id=session_id)

    # ---------- Round Management Methods ----------

    def append_round(
        self,
        qa_id: str,
        status: str,
        notes: Optional[str] = None,
        create_evidence_dir: bool = False,
    ) -> QARecord:
        """Append a new round to a QA record.

        This method:
        1. Increments the round number
        2. Creates corresponding evidence directory via EvidenceService
        3. Adds the round to round_history with status, notes, and date
        4. Saves the updated QA record

        Args:
            qa_id: QA record identifier
            status: Status for this round (canonical: approve|reject|blocked|pending)
            notes: Optional notes for this round (e.g., validator names)
            create_evidence_dir: Whether to create evidence directory (default True)

        Returns:
            Updated QA record with new round

        Raises:
            PersistenceError: If QA record not found
        """
        from datetime import datetime, timezone
        from ..evidence import EvidenceService

        qa = self.get(qa_id)
        if not qa:
            raise PersistenceError(f"QA record not found: {qa_id}")

        # Create corresponding evidence directory for the new round.
        #
        # IMPORTANT: Evidence directories may be created out-of-band (e.g. by other
        # processes/worktrees). When we append a round we must:
        # - never "go backwards" relative to existing evidence rounds
        # - ensure we create the next round directory deterministically
        if create_evidence_dir:
            ev_svc = EvidenceService(qa.task_id, project_root=self.project_root)
            ev_current = int(ev_svc.get_current_round() or 0)
            base = max(int(qa.round or 0), ev_current)
            next_round = base + 1
            # Ensure evidence directories exist sequentially. We may have QA round history
            # without evidence (e.g., `edison qa round` appends rounds without `--new`).
            # EvidenceService does not allow skipping (cannot create round-2 without round-1),
            # so we backfill the missing directories up to the next round.
            for rn in range(1, next_round + 1):
                ev_svc.ensure_round(rn)
            qa.round = int(next_round)
        else:
            # Increment round number (append semantics) when evidence is managed elsewhere.
            qa.round += 1

        # Add round entry to history
        round_entry: Dict[str, Any] = {
            "round": qa.round,
            "status": status,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        if notes:
            round_entry["notes"] = notes

        qa.round_history.append(round_entry)
        qa.metadata.touch()

        # Save the updated record
        self.save(qa)

        return qa

    def get_current_round(self, qa_id: str) -> int:
        """Get the current round number for a QA record.

        Args:
            qa_id: QA record identifier

        Returns:
            Current round number (1 if no QA found or initial round)
        """
        qa = self.get(qa_id)
        if not qa:
            return 1
        return qa.round

    def list_rounds(self, qa_id: str) -> List[Dict[str, Any]]:
        """List all rounds for a QA record.

        Args:
            qa_id: QA record identifier

        Returns:
            List of round entries (each with round, status, date, notes)
        """
        qa = self.get(qa_id)
        if not qa:
            return []
        return qa.round_history
    
    # ---------- File Format Helpers ----------

    def _qa_to_markdown(self, qa: QARecord, *, body: str | None = None) -> str:
        """Serialize a QA record as Markdown with YAML frontmatter.

        - State is NOT stored in frontmatter (derived from directory).
        - Body is preserved on saves; template is only used on creation.
        """
        from typing import Any, Dict

        # Build state history as serializable list
        state_history_data = None
        if qa.state_history:
            state_history_data = [h.to_dict() for h in qa.state_history]

        # Build frontmatter data (exclude None values)
        frontmatter_data: Dict[str, Any] = {
            "id": qa.id,
            "task_id": qa.task_id,
            "title": qa.title,
            "round": qa.round,
            "validator_owner": qa.validator_owner or qa.metadata.created_by,
            "session_id": qa.session_id,
            "validators": qa.validators if qa.validators else None,
            "evidence": qa.evidence if qa.evidence else None,
            "created_at": qa.metadata.created_at,
            "updated_at": qa.metadata.updated_at,
            "state_history": state_history_data,
            "round_history": qa.round_history if qa.round_history else None,
        }

        # Format as YAML frontmatter
        yaml_header = format_frontmatter(frontmatter_data, exclude_none=True)
        rendered_body = body if body is not None else self._render_qa_body(qa)
        return yaml_header + (rendered_body or "")

    def _render_qa_body(self, qa: QARecord) -> str:
        """Render the QA body from the composed template."""
        tpl_path = self._config.qa_template_path()
        if not tpl_path.exists():
            tpl_path = get_data_path("templates") / "documents" / "QA.md"
        raw = tpl_path.read_text(encoding="utf-8")
        body = strip_frontmatter_block(raw)
        return render_template_text(
            body,
            {
                "id": qa.id,
                "task_id": qa.task_id,
                "title": qa.title,
                "round": qa.round,
                "validator_owner": qa.validator_owner or qa.metadata.created_by,
            },
        )

    def _load_qa_from_file(self, path: Path) -> Optional[QARecord]:
        """Load a QA record from a markdown file."""
        # Tolerant load for directory scans/listings: ignore non-QA files and
        # skip legacy/unparseable content without failing the whole listing.
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                prefix = f.read(3)
                if prefix != "---":
                    return None
                content = prefix + f.read()

            if not has_frontmatter(content):
                return None
            return self._parse_qa_markdown(path.stem, content, path)
        except Exception:
            return None

    def _parse_qa_markdown(
        self,
        qa_id: str,
        content: str,
        path: Path,
    ) -> QARecord:
        """Parse QA record from markdown content with YAML frontmatter.

        State is ALWAYS derived from directory location, never from file content.

        Args:
            qa_id: QA ID from filename
            content: Markdown content with YAML frontmatter
            path: File path (for state derivation)

        Returns:
            QARecord instance
            
        Raises:
            ValueError: If content does not have valid YAML frontmatter
        """
        from edison.core.entity import StateHistoryEntry

        # State is ALWAYS derived from directory - single source of truth
        state = path.parent.name

        # Parse YAML frontmatter (only supported format)
        if not has_frontmatter(content):
            raise ValueError(
                f"QA record {qa_id} does not have YAML frontmatter."
            )

        doc = parse_frontmatter(content)
        fm = doc.frontmatter

        # Extract title from frontmatter or markdown heading
        title = fm.get("title", "")
        if not title:
            for line in doc.content.split("\n"):
                if parsed := parse_title(line):
                    title = parsed
                    break

        # Build state history from frontmatter
        state_history: List = []
        history_data = fm.get("state_history", [])
        if history_data:
            state_history = [StateHistoryEntry.from_dict(h) for h in history_data]

        # Build metadata
        metadata = EntityMetadata(
            created_at=fm.get("created_at", ""),
            updated_at=fm.get("updated_at", ""),
            created_by=fm.get("validator_owner"),
            session_id=fm.get("session_id"),
        )

        return QARecord(
            id=fm.get("id", qa_id),
            task_id=fm.get("task_id", ""),
            state=state,  # Always from directory
            title=title,
            session_id=fm.get("session_id"),
            validator_owner=fm.get("validator_owner"),
            metadata=metadata,
            state_history=state_history,
            validators=fm.get("validators", []) or [],
            evidence=fm.get("evidence", []) or [],
            round=fm.get("round", 1),
            round_history=fm.get("round_history", []) or [],
        )


__all__ = [
    "QARepository",
]
