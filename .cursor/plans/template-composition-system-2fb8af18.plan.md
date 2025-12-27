---
name: "Single Source of Truth: Task/QA Files as Canonical Data"
overview: ""
todos:
  - id: 3b86804b-a50f-4a3c-ab2c-8a436e1d80ad
    content: Create src/edison/data/templates/documents/TASK.md with YAML frontmatter
    status: pending
  - id: 68e9b3d2-9ff3-45a4-a24d-67b32e2e109e
    content: Create src/edison/data/templates/documents/QA.md with YAML frontmatter
    status: pending
  - id: 17a21061-332f-4b3b-83c9-f20c977ace51
    content: Create src/edison/core/utils/text/frontmatter.py for YAML parsing
    status: pending
  - id: 57ea7d3f-4503-4e68-8df7-42e202fe42f7
    content: Add depends_on, blocks_tasks, claimed_at, last_active, continuation_id to Task model
    status: pending
  - id: 7e34b086-2ba3-409d-9fc2-6c576135eec8
    content: Add all fields from QAEntry to QARecord model
    status: pending
  - id: a0adec27-cb71-4fbd-b02a-d14b367ad33a
    content: Update TaskRepository to use YAML frontmatter, derive state from directory
    status: pending
  - id: 691a30a1-819d-42d0-9f6c-796c5b630a16
    content: Update QARepository to use YAML frontmatter
    status: pending
  - id: c778eb19-c4f5-408a-9947-6d9cf7953065
    content: Create TaskIndex service for ripgrep-based task discovery
    status: pending
  - id: 8d5cce6b-f70d-4b51-9a1f-65da0bc74b9c
    content: Remove TaskEntry/QAEntry from Session, keep only session-level data
    status: pending
  - id: 0f040185-2f25-4b5a-b5f8-853d8ee34ec4
    content: Update graph.py to use TaskIndex instead of session JSON
    status: pending
  - id: 3046c8f8-c177-45a8-92b8-05f9313a8995
    content: Update workflow.py to write only to files, no session JSON
    status: pending
  - id: b64f926d-26e7-4c0d-b3f2-f390c408a1e9
    content: Create DocumentTemplateRegistry for template composition
    status: pending
  - id: 2b9eab73-8f44-446c-8bc3-9f130c0d4b06
    content: Add --documents flag to edison compose --all
    status: pending
  - id: e3a9b0fd-94d7-4382-82d0-820a01703fa1
    content: Create migration script to convert existing tasks to YAML frontmatter
    status: pending
---

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