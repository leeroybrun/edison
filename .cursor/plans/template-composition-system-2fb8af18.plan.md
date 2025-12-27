<!-- 2fb8af18-af0c-40b4-a740-da7082398f2a f3664980-2718-4de1-81c9-18ca80325428 -->
# Single Source of Truth: Task/QA Files as Canonical Data

## Problem Statement

Edison currently has a **dual-write architecture** that causes drift:

1. Task/QA markdown files store basic metadata (Owner, Status, Session)
2. Session JSON stores rich tracking data (parentId, childIds, claimedAt, lastActive, automation, etc.)

Every state change writes to BOTH, and if either fails, they desync. Fields like `DependsOn`, `BlocksTask` in task files are never parsed - they're decoration only.

## Solution: Single Source of Truth

**Task/QA files become THE canonical source for all task/QA data.**

### New Architecture

```
Task/QA Files (Single Source of Truth)
├── State: Derived from directory location (.project/tasks/{state}/)
├── Metadata: YAML frontmatter (all fields)
└── Content: Markdown body

Session Files (Session-Level Data Only)
├── Session metadata: id, state, phase, owner, createdAt, lastActive
├── Git info: worktreePath, branchName, baseBranch
├── Activity log: Session-level history
└── NO task/QA entries (derived from files on demand)
```

### Task File Format (New)

```yaml
---
id: "task-150-auth-gate"
owner: claude
session_id: python-pid-123
parent_id: task-100
child_ids:
 - task-151
 - task-152
depends_on:
 - task-50
blocks_tasks:
 - task-200
claimed_at: "2025-12-03T10:00:00Z"
last_active: "2025-12-03T11:30:00Z"
continuation_id: zen-abc123
created_at: "2025-12-03T09:00:00Z"
updated_at: "2025-12-03T11:30:00Z"
---

# Auth Gate Implementation

Task description and details...
```

**Note**: Status is NOT in frontmatter - it's derived from the directory the file is in (`.project/tasks/wip/` = wip status).

### QA File Format (New)

```yaml
---
id: "task-150-auth-gate-qa"
task_id: "task-150-auth-gate"
round: 1
validator_owner: codex
session_id: python-pid-123
validators:
 - security
 - api
evidence:
 - ".project/qa/validation-evidence/task-150/round-1/bundle-approved.json"
created_at: "2025-12-03T09:00:00Z"
updated_at: "2025-12-03T11:30:00Z"
state_history:
 - from: waiting
    to: todo
    timestamp: "2025-12-03T10:00:00Z"
    reason: task_completed
---

# QA for task-150-auth-gate: Auth Gate Implementation

Validation details...
```

### Fast Parsing Strategy

Use ripgrep to extract frontmatter from all task files, then parse YAML:

```bash
# Extract all task frontmatter in one pass
rg -U --multiline "^---\n([\s\S]*?)\n---" .project/tasks/ --json
```

Then parse each YAML block with Python's `yaml.safe_load()`.

## Implementation Plan

### Phase 1: Create YAML Frontmatter Templates

1. **Create core task template** [`src/edison/data/templates/documents/TASK.md`](src/edison/data/templates/documents/TASK.md)

                                                                                                - YAML frontmatter with ALL task fields
                                                                                                - Handlebars variables for dynamic values
                                                                                                - Extensible sections for packs/project

2. **Create core QA template** [`src/edison/data/templates/documents/QA.md`](src/edison/data/templates/documents/QA.md)

                                                                                                - YAML frontmatter with ALL QA fields
                                                                                                - Evidence section structure

### Phase 2: Update Parsing Layer

3. **Create frontmatter parser** [`src/edison/core/utils/text/frontmatter.py`](src/edison/core/utils/text/frontmatter.py)

                                                                                                - `parse_frontmatter(content: str) -> dict` - Extract and parse YAML
                                                                                                - `format_frontmatter(data: dict) -> str` - Format dict as YAML frontmatter
                                                                                                - Batch extraction support for ripgrep integration

4. **Update TaskRepository** [`src/edison/core/task/repository.py`](src/edison/core/task/repository.py)

                                                                                                - `_parse_task_markdown()` - Use frontmatter parser, derive state from directory
                                                                                                - `_task_to_markdown()` - Generate YAML frontmatter
                                                                                                - Add all new fields to Task model

5. **Update QARepository** [`src/edison/core/qa/workflow/repository.py`](src/edison/core/qa/workflow/repository.py)

                                                                                                - Same changes as TaskRepository

### Phase 3: Update Task

### To-dos

- [ ] Create src/edison/data/templates/documents/TASK.md with YAML frontmatter
- [ ] Create src/edison/data/templates/documents/QA.md with YAML frontmatter
- [ ] Create src/edison/core/utils/text/frontmatter.py for YAML parsing
- [ ] Add depends_on, blocks_tasks, claimed_at, last_active, continuation_id to Task model
- [ ] Add all fields from QAEntry to QARecord model
- [ ] Update TaskRepository to use YAML frontmatter, derive state from directory
- [ ] Update QARepository to use YAML frontmatter
- [ ] Create TaskIndex service for ripgrep-based task discovery
- [ ] Remove TaskEntry/QAEntry from Session, keep only session-level data
- [ ] Update graph.py to use TaskIndex instead of session JSON
- [ ] Update workflow.py to write only to files, no session JSON
- [ ] Create DocumentTemplateRegistry for template composition
- [ ] Add --documents flag to edison compose --all
- [ ] Create migration script to convert existing tasks to YAML frontmatter