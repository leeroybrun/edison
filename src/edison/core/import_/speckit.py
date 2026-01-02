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

from edison.core.import_.sync import SyncResult, sync_items_to_tasks
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository
from edison.core.entity import EntityMetadata
from edison.core.utils.paths import safe_relpath


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
        has_research: Whether research.md exists
        has_quickstart: Whether quickstart.md exists
        has_checklists: Whether checklists/ directory exists
    """

    name: str
    path: Path
    tasks: List[SpecKitTask] = field(default_factory=list)
    has_spec: bool = False
    has_plan: bool = False
    has_data_model: bool = False
    has_contracts: bool = False
    has_research: bool = False
    has_quickstart: bool = False
    has_checklists: bool = False


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
        has_research=(folder_path / "research.md").exists(),
        has_quickstart=(folder_path / "quickstart.md").exists(),
        has_checklists=(folder_path / "checklists").is_dir(),
    )


# =============================================================================
# GENERATOR FUNCTIONS
# =============================================================================


def generate_edison_task(
    speckit_task: SpecKitTask,
    feature: SpecKitFeature,
    prefix: str,
    *,
    project_root: Path,
    depends_on: Optional[list[str]] = None,
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
    description = generate_task_description(speckit_task, feature, project_root=project_root)

    return Task(
        id=task_id,
        state="todo",
        title=speckit_task.description,
        description=description,
        tags=tags,
        depends_on=list(depends_on or []),
        integration={
            "kind": "speckit",
            "speckit": {
                "feature_dir": safe_relpath(feature.path, project_root=project_root),
                "tasks_md": safe_relpath(feature.path / "tasks.md", project_root=project_root),
                "task_id": speckit_task.id,
            },
        },
        metadata=EntityMetadata.create(created_by="speckit-import"),
    )


def generate_task_description(
    speckit_task: SpecKitTask,
    feature: SpecKitFeature,
    *,
    project_root: Path,
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
    tasks_md_rel = safe_relpath(feature.path / "tasks.md", project_root=project_root)
    plan_md_rel = safe_relpath(feature.path / "plan.md", project_root=project_root)

    lines = [
        f"**SpecKit Source**: `{tasks_md_rel}` -> {speckit_task.id}",
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

    # Workflow block (mirrors Spec Kit /speckit.implement intent, without replacing Edison workflow)
    lines.extend(
        [
            "",
            "## Workflow (MUST FOLLOW)",
            "1. Read **Required Reading** below before editing code.",
        ]
    )
    if feature.has_checklists:
        lines.append(
            f"2. Review `{safe_relpath(feature.path / 'checklists', project_root=project_root)}/` and ensure all checklists are complete before proceeding (or explicitly document why proceeding)."
        )
    else:
        lines.append(
            "2. If a `checklists/` directory exists for this feature, ensure all checklists are complete before proceeding (or explicitly document why proceeding)."
        )
    lines.append(
        f"3. Keep `{tasks_md_rel}` in sync: mark `{speckit_task.id}` as completed (`- [x]`) when this task is complete. Edison will also attempt to sync this automatically when the task is marked `validated`."
    )

    # Add required reading section with links to available docs (tasks.md + plan.md are Spec Kit prerequisites)
    reading_links = [f"- `{tasks_md_rel}`"]
    if feature.has_plan:
        reading_links.append(f"- `{plan_md_rel}`")
    else:
        reading_links.append(f"- `{plan_md_rel}` (MISSING: generate via Spec Kit /speckit.plan)")

    if feature.has_spec:
        spec_md_rel = safe_relpath(feature.path / "spec.md", project_root=project_root)
        link = f"- `{spec_md_rel}`"
        if speckit_task.user_story:
            link += f" -> User Story {speckit_task.user_story}"
        reading_links.append(link)

    if feature.has_data_model:
        reading_links.append(f"- `{safe_relpath(feature.path / 'data-model.md', project_root=project_root)}`")

    if feature.has_contracts:
        reading_links.append(f"- `{safe_relpath(feature.path / 'contracts', project_root=project_root)}/`")

    if feature.has_research:
        reading_links.append(f"- `{safe_relpath(feature.path / 'research.md', project_root=project_root)}`")

    if feature.has_quickstart:
        reading_links.append(f"- `{safe_relpath(feature.path / 'quickstart.md', project_root=project_root)}`")

    if reading_links:
        lines.extend([
            "",
            "## Required Reading (MUST)",
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
    prefix = prefix or feature.name

    # Initialize repository
    task_repo = TaskRepository(project_root)
    resolved_project_root = task_repo.project_root

    depends_map = _compute_speckit_depends_on(feature.tasks)
    edison_depends = {
        tid: [f"{prefix}-{dep}" for dep in deps]
        for tid, deps in depends_map.items()
    }

    return sync_items_to_tasks(
        feature.tasks,
        task_repo=task_repo,
        item_key=lambda t: t.id,
        build_task=lambda t: generate_edison_task(
            t,
            feature,
            prefix,
            project_root=resolved_project_root,
            depends_on=edison_depends.get(t.id, []),
        ),
        update_task=lambda task, t: _update_edison_task(
            task,
            t,
            feature,
            project_root=resolved_project_root,
            depends_on=edison_depends.get(t.id, []),
        ),
        is_managed_task=lambda t: t.id.startswith(f"{prefix}-T"),
        task_key=lambda t: _extract_speckit_id(t.id, prefix),
        removed_tag="removed-from-spec",
        create_qa=create_qa,
        qa_created_by="speckit-import",
        dry_run=dry_run,
        project_root=resolved_project_root,
        updatable_states={"todo"},
    )


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

def _extract_speckit_id(edison_id: str, prefix: str) -> str:
    """Extract SpecKit task ID from Edison task ID.

    Example: "auth-T001" with prefix "auth" -> "T001"
    """
    return edison_id[len(prefix) + 1:]  # Skip "prefix-"

def _update_edison_task(
    task: Task,
    speckit_task: SpecKitTask,
    feature: SpecKitFeature,
    *,
    project_root: Path,
    depends_on: list[str],
) -> None:
    """Update an existing Edison task with new SpecKit data.

    Mutates the task in-place; caller is responsible for saving.
    """
    # Update title and description
    task.title = speckit_task.description
    task.description = generate_task_description(
        speckit_task, feature, project_root=project_root
    )

    task.integration = {
        "kind": "speckit",
        "speckit": {
            "feature_dir": safe_relpath(feature.path, project_root=project_root),
            "tasks_md": safe_relpath(feature.path / "tasks.md", project_root=project_root),
            "task_id": speckit_task.id,
        },
    }
    task.depends_on = list(depends_on or [])

    # Update tags
    if "speckit" not in task.tags:
        task.tags.append("speckit")


def _compute_speckit_depends_on(tasks: list[SpecKitTask]) -> dict[str, list[str]]:
    """Compute dependency ordering from SpecKit tasks.md.

    Spec Kit's execution flow is primarily order- and phase-driven, with `[P]` marking
    tasks that can run in parallel *within the current phase*.

    Edison uses `depends_on` to enforce claim order. This mapping is a conservative
    approximation of Spec Kit's intent:
    - Phase-by-phase: any task in a later phase depends on all tasks in the previous phase.
    - Within a phase:
      - Non-[P] tasks depend on all prior tasks in the phase (sequential barrier).
      - [P] tasks depend on the most recent sequential barrier task (and the phase gate).
    - File conflicts: if a [P] task targets a file already targeted in the current wave,
      treat it as non-parallel for ordering purposes.
    """
    deps: dict[str, list[str]] = {}

    wave: list[SpecKitTask] = []
    wave_files: set[str] = set()
    barrier_id: str | None = None
    phase_gate: list[str] = []
    current_phase: str | None = None

    for task in tasks:
        if current_phase is None:
            current_phase = task.phase
        elif task.phase != current_phase:
            # Close previous phase: next phase tasks must wait for all prior tasks.
            phase_gate = [t.id for t in wave]
            wave = []
            wave_files = set()
            barrier_id = None
            current_phase = task.phase

        is_parallel = bool(task.parallel)
        if is_parallel and task.target_file and task.target_file in wave_files:
            is_parallel = False

        if is_parallel:
            d = list(phase_gate)
            if barrier_id:
                d.append(barrier_id)
            deps[task.id] = d
            wave.append(task)
            if task.target_file:
                wave_files.add(task.target_file)
        else:
            d = list(phase_gate) + [t.id for t in wave]
            deps[task.id] = d
            wave.append(task)
            if task.target_file:
                wave_files.add(task.target_file)
            barrier_id = task.id

    # Within the first phase, phase_gate is empty; deps already computed.
    return deps


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
