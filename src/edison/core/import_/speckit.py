"""SpecKit import module for Edison.

This module provides functionality to import SpecKit tasks into Edison's
task management system. It supports:
- Parsing SpecKit tasks.md files
- Parsing SpecKit feature folders
- Generating Edison tasks with links to spec docs
- Syncing/re-importing when specs change

SpecKit tasks are imported as "thin" Edison tasks that **link** to
spec documents (no embedding). The spec folder remains the single
source of truth, eliminating drift when specs change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository
from edison.core.entity import EntityMetadata


class SpecKitImportError(Exception):
    """Error during SpecKit import operation."""

    pass


@dataclass
class SpecKitTask:
    """Parsed task from SpecKit tasks.md.

    Attributes:
        id: Task ID (T001, T002, etc.)
        parallel: Whether task can be run in parallel [P] marker
        user_story: User story reference (US1, US2, etc.)
        description: Full task description
        target_file: Extracted target file path if present
        phase: Task phase (setup, foundational, user-story-N, polish)
        completed: Whether task is marked completed [x]
    """

    id: str
    parallel: bool = False
    user_story: Optional[str] = None
    description: str = ""
    target_file: Optional[str] = None
    phase: str = "setup"
    completed: bool = False


@dataclass
class SpecKitFeature:
    """Parsed SpecKit feature folder metadata.

    Attributes:
        name: Feature folder name
        path: Full path to feature folder
        tasks: List of parsed tasks
        has_spec: Whether spec.md exists
        has_plan: Whether plan.md exists
        has_data_model: Whether data-model.md exists
        has_contracts: Whether contracts/ directory exists
    """

    name: str
    path: Path
    tasks: List[SpecKitTask] = field(default_factory=list)
    has_spec: bool = False
    has_plan: bool = False
    has_data_model: bool = False
    has_contracts: bool = False


@dataclass
class SyncResult:
    """Result of import/sync operation.

    Attributes:
        created: List of new task IDs created
        updated: List of existing task IDs updated
        flagged: List of task IDs flagged as removed from spec
        skipped: List of task IDs skipped (already in progress/done)
        errors: List of error messages encountered
    """

    created: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    flagged: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# =============================================================================
# PATTERNS
# =============================================================================

# Pattern to match task lines: - [ ] T001 [P?] [US#?] Description
# Captures: checkbox_state, task_id, rest_of_line
TASK_LINE_PATTERN = re.compile(
    r"^-\s*\[([xX\s])\]\s*"  # Checkbox: - [ ] or - [x] or - [X]
    r"(T\d+)\s+"  # Task ID: T001, T002, etc.
    r"(.+)$"  # Rest of line (markers + description)
)

# Pattern to extract [P] parallel marker
PARALLEL_MARKER_PATTERN = re.compile(r"\[P\]\s*")

# Pattern to extract [US#] user story marker
USER_STORY_PATTERN = re.compile(r"\[US(\d+)\]\s*")

# Pattern to extract file paths from descriptions
# Matches: "in path/to/file.ext" or "at path/to/file.ext"
FILE_PATH_PATTERN = re.compile(r"\b(?:in|at)\s+([^\s]+\.\w+)")

# Pattern to detect phase headers
# Examples: "## Phase 1: Setup", "## Phase 2: Foundational", "## Phase 3: User Story 1"
# Also handles "## Phase N: Polish" where N is a letter
PHASE_HEADER_PATTERN = re.compile(
    r"^##\s*Phase\s+\w+:\s*(.+)$", re.IGNORECASE
)


# =============================================================================
# PARSER FUNCTIONS
# =============================================================================


def parse_tasks_md(content: str) -> List[SpecKitTask]:
    """Parse SpecKit tasks.md content into task objects.

    Parses the checklist format used by SpecKit:
    - [ ] T001 [P?] [US#?] Description

    Args:
        content: Raw content of tasks.md file

    Returns:
        List of parsed SpecKitTask objects
    """
    if not content.strip():
        return []

    tasks: List[SpecKitTask] = []
    current_phase = "setup"

    for line in content.split("\n"):
        line = line.strip()

        # Check for phase headers
        phase_match = PHASE_HEADER_PATTERN.match(line)
        if phase_match:
            phase_name = phase_match.group(1).strip().lower()
            current_phase = _normalize_phase_name(phase_name)
            continue

        # Check for task lines
        task_match = TASK_LINE_PATTERN.match(line)
        if task_match:
            checkbox_state = task_match.group(1)
            task_id = task_match.group(2)
            rest = task_match.group(3)

            # Parse markers and description from rest of line
            parallel, user_story, description = _parse_task_markers(rest)

            # Extract target file from description
            target_file = _extract_file_path(description)

            task = SpecKitTask(
                id=task_id,
                parallel=parallel,
                user_story=user_story,
                description=description,
                target_file=target_file,
                phase=current_phase,
                completed=checkbox_state.lower() == "x",
            )
            tasks.append(task)

    return tasks


def parse_feature_folder(path: Path) -> SpecKitFeature:
    """Parse a SpecKit feature folder.

    A feature folder typically contains:
    - tasks.md (required): Task checklist
    - spec.md (optional): Feature specification
    - plan.md (optional): Implementation plan
    - data-model.md (optional): Data model definitions
    - contracts/ (optional): API contracts directory

    Args:
        path: Path to feature folder or tasks.md file

    Returns:
        SpecKitFeature object with parsed metadata

    Raises:
        SpecKitImportError: If tasks.md is not found
    """
    path = Path(path)

    # Handle both folder path and direct tasks.md path
    if path.is_file() and path.name == "tasks.md":
        folder_path = path.parent
    else:
        folder_path = path

    tasks_file = folder_path / "tasks.md"
    if not tasks_file.exists():
        raise SpecKitImportError(f"tasks.md not found in {folder_path}")

    # Parse tasks
    content = tasks_file.read_text(encoding="utf-8")
    tasks = parse_tasks_md(content)

    # Check for optional docs
    return SpecKitFeature(
        name=folder_path.name,
        path=folder_path,
        tasks=tasks,
        has_spec=(folder_path / "spec.md").exists(),
        has_plan=(folder_path / "plan.md").exists(),
        has_data_model=(folder_path / "data-model.md").exists(),
        has_contracts=(folder_path / "contracts").is_dir(),
    )


# =============================================================================
# GENERATOR FUNCTIONS
# =============================================================================


def generate_edison_task(
    speckit_task: SpecKitTask,
    feature: SpecKitFeature,
    prefix: str,
) -> Task:
    """Generate an Edison Task from a SpecKit task.

    Creates a "thin" Edison task that links to spec documents rather than
    embedding their content. This prevents drift when specs change.

    Args:
        speckit_task: Parsed SpecKit task
        feature: Feature folder metadata
        prefix: Task ID prefix (e.g., "auth" -> "auth-T001")

    Returns:
        Edison Task object ready for persistence
    """
    task_id = f"{prefix}-{speckit_task.id}"

    # Build tags
    tags = ["speckit", prefix]
    if speckit_task.user_story:
        # Convert US1 -> user-story-1
        story_num = speckit_task.user_story.replace("US", "")
        tags.append(f"user-story-{story_num}")

    # Generate description with links
    description = generate_task_description(speckit_task, feature)

    return Task(
        id=task_id,
        state="todo",
        title=speckit_task.description,
        description=description,
        tags=tags,
        metadata=EntityMetadata.create(created_by="speckit-import"),
    )


def generate_task_description(
    speckit_task: SpecKitTask,
    feature: SpecKitFeature,
) -> str:
    """Generate Edison task description with links to spec docs.

    Creates a structured description that links to the source spec
    documents rather than embedding their content.

    Args:
        speckit_task: Parsed SpecKit task
        feature: Feature folder metadata

    Returns:
        Markdown description with links
    """
    # Get relative spec path for display
    spec_path = f"specs/{feature.name}"

    lines = [
        f"**SpecKit Source**: `{spec_path}/tasks.md` -> {speckit_task.id}",
        f"**Feature**: {feature.name}",
    ]

    # Add phase and user story info
    phase_info = f"**Phase**: {speckit_task.phase}"
    if speckit_task.user_story:
        phase_info += f" | **User Story**: {speckit_task.user_story}"
    if speckit_task.parallel:
        phase_info += " | **Parallelizable**: Yes"
    lines.append(phase_info)

    # Add implementation target if present
    if speckit_task.target_file:
        lines.extend([
            "",
            "## Implementation Target",
            f"`{speckit_task.target_file}`",
        ])

    # Add required reading section with links to available docs
    reading_links = []
    if feature.has_spec:
        link = f"- `{spec_path}/spec.md`"
        if speckit_task.user_story:
            link += f" -> User Story {speckit_task.user_story}"
        reading_links.append(link)

    if feature.has_data_model:
        reading_links.append(f"- `{spec_path}/data-model.md`")

    if feature.has_contracts:
        reading_links.append(f"- `{spec_path}/contracts/`")

    if feature.has_plan:
        reading_links.append(f"- `{spec_path}/plan.md`")

    if reading_links:
        lines.extend([
            "",
            "## Required Reading",
            "Before implementing this task, read:",
        ])
        lines.extend(reading_links)

    # Add original task reference
    original = f"> {speckit_task.id}"
    if speckit_task.parallel:
        original += " [P]"
    if speckit_task.user_story:
        original += f" [{speckit_task.user_story}]"
    original += f" {speckit_task.description}"

    lines.extend([
        "",
        "## Original SpecKit Task",
        original,
    ])

    return "\n".join(lines)


# =============================================================================
# SYNC FUNCTIONS
# =============================================================================


def sync_speckit_feature(
    feature: SpecKitFeature,
    *,
    prefix: Optional[str] = None,
    create_qa: bool = True,
    dry_run: bool = False,
    project_root: Optional[Path] = None,
) -> SyncResult:
    """Import or sync a SpecKit feature with Edison tasks.

    On first import, creates Edison tasks for all SpecKit tasks.
    On re-sync, it:
    - Updates metadata for existing tasks (if changed)
    - Creates new Edison tasks for new SpecKit tasks
    - Flags Edison tasks whose SpecKit source was removed
    - Preserves Edison task state (wip, done, validated)

    Args:
        feature: Parsed SpecKit feature
        prefix: Task ID prefix (defaults to feature name)
        create_qa: Whether to create QA records (default True)
        dry_run: Preview changes without writing (default False)
        project_root: Project root directory

    Returns:
        SyncResult with created, updated, flagged, skipped task IDs
    """
    result = SyncResult()
    prefix = prefix or feature.name

    # Initialize repository
    task_repo = TaskRepository(project_root)

    # Build map of SpecKit task IDs in this feature
    speckit_ids = {task.id for task in feature.tasks}

    # Find existing Edison tasks for this prefix
    existing_tasks = _find_tasks_with_prefix(task_repo, prefix)
    existing_map = {_extract_speckit_id(t.id, prefix): t for t in existing_tasks}

    # Process each SpecKit task
    for speckit_task in feature.tasks:
        edison_id = f"{prefix}-{speckit_task.id}"

        if speckit_task.id in existing_map:
            # Task already exists - check if needs update
            existing = existing_map[speckit_task.id]

            # Preserve state for tasks in progress
            if existing.state not in ("todo",):
                result.skipped.append(edison_id)
                continue

            # Update the task
            if not dry_run:
                _update_edison_task(task_repo, existing, speckit_task, feature)
            result.updated.append(edison_id)
        else:
            # New task - create it
            if not dry_run:
                task = generate_edison_task(speckit_task, feature, prefix)
                task_repo.save(task)

                # Create QA record if enabled
                if create_qa:
                    _create_qa_record(task.id, project_root)

            result.created.append(edison_id)

    # Check for removed tasks (in Edison but not in SpecKit)
    for speckit_id, existing in existing_map.items():
        if speckit_id not in speckit_ids:
            edison_id = existing.id
            if not dry_run:
                _flag_task_as_removed(task_repo, existing)
            result.flagged.append(edison_id)

    return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _normalize_phase_name(phase_name: str) -> str:
    """Normalize phase name to standard format.

    Converts phase header text to standardized slug:
    - "Setup" -> "setup"
    - "Foundational" -> "foundational"
    - "User Story 1 - Authentication" -> "user-story-1"
    - "Polish" -> "polish"
    """
    phase_lower = phase_name.lower()

    if "setup" in phase_lower:
        return "setup"
    if "foundational" in phase_lower:
        return "foundational"
    if "polish" in phase_lower:
        return "polish"

    # Check for user story pattern
    us_match = re.search(r"user\s*story\s*(\d+)", phase_lower)
    if us_match:
        return f"user-story-{us_match.group(1)}"

    # Default to lowercased, hyphenated version
    return re.sub(r"\s+", "-", phase_lower.strip())


def _parse_task_markers(text: str) -> tuple[bool, Optional[str], str]:
    """Parse task markers from the rest of the task line.

    Extracts [P] and [US#] markers and returns clean description.

    Args:
        text: Text after task ID

    Returns:
        Tuple of (parallel, user_story, description)
    """
    parallel = False
    user_story = None

    # Check for [P] marker
    if PARALLEL_MARKER_PATTERN.search(text):
        parallel = True
        text = PARALLEL_MARKER_PATTERN.sub("", text)

    # Check for [US#] marker
    us_match = USER_STORY_PATTERN.search(text)
    if us_match:
        user_story = f"US{us_match.group(1)}"
        text = USER_STORY_PATTERN.sub("", text)

    return parallel, user_story, text.strip()


def _extract_file_path(description: str) -> Optional[str]:
    """Extract file path from task description.

    Looks for patterns like "in path/to/file.py" or "at path/to/file.ts".
    """
    match = FILE_PATH_PATTERN.search(description)
    if match:
        return match.group(1)
    return None


def _find_tasks_with_prefix(repo: TaskRepository, prefix: str) -> List[Task]:
    """Find all Edison tasks with the given prefix."""
    all_tasks = repo.find_all()
    return [t for t in all_tasks if t.id.startswith(f"{prefix}-T")]


def _extract_speckit_id(edison_id: str, prefix: str) -> str:
    """Extract SpecKit task ID from Edison task ID.

    Example: "auth-T001" with prefix "auth" -> "T001"
    """
    return edison_id[len(prefix) + 1:]  # Skip "prefix-"


def _update_edison_task(
    repo: TaskRepository,
    task: Task,
    speckit_task: SpecKitTask,
    feature: SpecKitFeature,
) -> None:
    """Update an existing Edison task with new SpecKit data."""
    # Update title and description
    task.title = speckit_task.description
    task.description = generate_task_description(speckit_task, feature)

    # Update tags
    if "speckit" not in task.tags:
        task.tags.append("speckit")

    repo.save(task)


def _flag_task_as_removed(repo: TaskRepository, task: Task) -> None:
    """Flag a task as removed from spec."""
    if "removed-from-spec" not in task.tags:
        task.tags.append("removed-from-spec")
        repo.save(task)


def _create_qa_record(task_id: str, project_root: Optional[Path]) -> None:
    """Create a QA record for a task."""
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.qa.models import QARecord
    from edison.core.entity import EntityMetadata

    qa_repo = QARepository(project_root)
    qa = QARecord(
        id=f"{task_id}-qa",
        task_id=task_id,
        state="waiting",
        title=f"QA {task_id}",
        metadata=EntityMetadata.create(created_by="speckit-import"),
    )
    qa_repo.save(qa)


__all__ = [
    "SpecKitTask",
    "SpecKitFeature",
    "SyncResult",
    "SpecKitImportError",
    "parse_tasks_md",
    "parse_feature_folder",
    "generate_edison_task",
    "generate_task_description",
    "sync_speckit_feature",
]
