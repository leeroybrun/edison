# SpecKit Integration

**Importing GitHub's SpecKit tasks into Edison**

---

## Overview

Edison integrates with [SpecKit](https://github.com/github/spec-kit), GitHub's Spec-Driven Development (SDD) tool. This allows you to:

1. Generate comprehensive specs and task lists using SpecKit's AI-powered workflow
2. Import those tasks into Edison for implementation and QA validation
3. Re-sync when specs evolve, preserving your work in progress

### Design Philosophy: Thin Tasks with Links

Edison imports SpecKit tasks as **thin references** that link back to the spec documents rather than embedding their content. This design:

- **Prevents drift** - When specs change, tasks still point to the current version
- **Enables re-import** - Safe to sync when specs evolve
- **Maintains single source of truth** - The spec folder remains authoritative

```
SpecKit Feature Folder              Edison Tasks
---------------------              -------------
specs/auth-feature/                .project/tasks/todo/
├── spec.md                        auth-T001.md ──┐
├── plan.md          <─────────────auth-T002.md   │ LINKS TO
├── data-model.md    <─────────────auth-T003.md   │ (no embedding)
├── contracts/       <─────────────...           ─┘
└── tasks.md ────────► SYNC ──────►
```

---

## Quick Start

### 1. Generate Specs with SpecKit

First, use SpecKit to create your feature specs:

```bash
# Using SpecKit's Claude workflow
cd your-project
# Create specs/my-feature/ with spec.md, plan.md, data-model.md, tasks.md
```

### 2. Import into Edison

```bash
# Import a SpecKit feature
edison import speckit specs/my-feature/

# Preview without making changes
edison import speckit specs/my-feature/ --dry-run

# Custom task prefix
edison import speckit specs/my-feature/ --prefix auth

# Skip QA record creation
edison import speckit specs/my-feature/ --no-qa
```

### 3. Work on Tasks

Tasks appear in `.project/tasks/todo/` with links to the spec documents:

```bash
edison task list
edison task claim auth-T001
```

### 4. Re-sync When Specs Change

```bash
# Specs evolved? Re-import to sync
edison import speckit specs/my-feature/
```

---

## CLI Reference

### `edison import speckit`

Import or sync SpecKit tasks into Edison.

**Usage:**
```bash
edison import speckit <source> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `source` | Path to SpecKit feature folder or tasks.md file |

**Options:**

| Option | Description |
|--------|-------------|
| `--prefix <name>` | Custom task ID prefix (default: folder name) |
| `--dry-run` | Preview changes without writing files |
| `--no-qa` | Skip creating QA records for imported tasks |
| `--json` | Output results as JSON |
| `--repo-root <path>` | Override repository root path |

**Examples:**

```bash
# Basic import
edison import speckit specs/auth-feature/

# Import with custom prefix
edison import speckit specs/authentication/ --prefix auth

# Preview what would happen
edison import speckit specs/payment/ --dry-run

# JSON output for scripting
edison import speckit specs/feature/ --json
```

---

## SpecKit Task Format

Edison parses the standard SpecKit tasks.md checklist format:

```markdown
## Phase 1: Setup

- [ ] T001 Create project structure
- [ ] T002 [P] Initialize dependencies
- [x] T003 Configure linting (already done)

## Phase 2: User Story 1 - Authentication

- [ ] T010 [US1] Create User model in src/models/user.py
- [ ] T011 [P] [US1] Create UserService in src/services/user.py
```

### Task Markers

| Marker | Meaning |
|--------|---------|
| `T###` | Task ID (required) |
| `[P]` | Parallelizable - can run concurrently with other tasks |
| `[US#]` | User Story reference |
| `[x]` | Already completed |

### Phase Detection

Edison detects phases from section headers:
- `## Phase 1: Setup` → `setup`
- `## Phase 2: Foundational` → `foundational`
- `## Phase 3: User Story 1` → `user-story-1`
- `## Phase N: Polish` → `polish`

### File Path Extraction

Edison extracts target files from descriptions:
- `Create model in src/models/user.py` → target: `src/models/user.py`
- `Add component at src/components/Button.tsx` → target: `src/components/Button.tsx`

---

## Generated Task Format

Each imported Edison task contains links to spec documents:

```markdown
---
id: auth-T012
title: Create User model in src/models/user.py
tags:
  - speckit
  - auth
  - user-story-1
---

# Create User model in src/models/user.py

**SpecKit Source**: `specs/auth/tasks.md` → T012
**Feature**: auth
**Phase**: user-story-1 | **User Story**: US1 | **Parallelizable**: Yes

## Implementation Target
`src/models/user.py`

## Required Reading
Before implementing this task, read:
- `specs/auth/spec.md` → User Story US1
- `specs/auth/data-model.md`
- `specs/auth/contracts/`
- `specs/auth/plan.md`

## Original SpecKit Task
> T012 [P] [US1] Create User model in src/models/user.py
```

---

## Sync Behavior

When re-importing a feature, Edison handles changes intelligently:

| Edison State | SpecKit State | Action |
|--------------|---------------|--------|
| Task exists in `todo` | Task in tasks.md | **Update** metadata if changed |
| Task exists in `wip`/`done` | Task in tasks.md | **Skip** (preserve Edison state) |
| Task exists | Task removed | **Flag** with `removed-from-spec` tag |
| (none) | New task | **Create** new Edison task |

### Key Sync Rules

1. **Match by SpecKit ID** - Tasks matched by their T### ID within the prefix
2. **Never reset work** - Tasks in `wip` or `done` are never reset to `todo`
3. **Flag removals** - Removed tasks get tagged, not deleted
4. **Update descriptions** - Title and metadata changes are applied

---

## Feature Folder Structure

Edison recognizes these files in a SpecKit feature folder:

| File/Dir | Purpose | Used In |
|----------|---------|---------|
| `tasks.md` | Task checklist (required) | Task parsing |
| `spec.md` | Feature specification | Required Reading links |
| `plan.md` | Implementation plan | Required Reading links |
| `data-model.md` | Data model definitions | Required Reading links |
| `contracts/` | API contracts | Required Reading links |

Only `tasks.md` is required. Other files enhance the "Required Reading" section in generated tasks.

---

## Workflow Integration

### Typical SpecKit → Edison Workflow

```bash
# 1. Create feature spec with SpecKit (using Claude)
# Result: specs/my-feature/ with tasks.md, spec.md, plan.md, etc.

# 2. Import into Edison
edison import speckit specs/my-feature/

# 3. Start Edison session
edison session create --goal "Implement my-feature"

# 4. Work on tasks
edison task claim my-feature-T001
# ... implement, reading specs as directed ...
edison task mark-done my-feature-T001

# 5. QA validation
edison qa run my-feature-T001

# 6. If specs change, re-sync
edison import speckit specs/my-feature/
```

### Integration with Session Workflow

Imported SpecKit tasks work seamlessly with Edison's session system:

```bash
# Tasks appear in your session's available work
edison session next  # May suggest a SpecKit-imported task

# Delegation to agents works normally
edison task claim my-feature-T005
# Agent reads "Required Reading" section to understand context
```

---

## Troubleshooting

### "tasks.md not found"

Ensure your source path points to a valid SpecKit feature folder containing `tasks.md`:

```bash
# Check the folder exists
ls specs/my-feature/tasks.md
```

### Tasks Not Updating on Re-sync

Tasks in `wip` or `done` state are intentionally preserved. To force an update:

1. Move the task back to `todo` state
2. Re-run the import

### Duplicate Task IDs

If you have multiple features with the same task IDs, use the `--prefix` flag:

```bash
edison import speckit specs/auth/ --prefix auth
edison import speckit specs/payment/ --prefix payment
```

---

## API Reference

For programmatic access, use the core module:

```python
from edison.core.import_.speckit import (
    parse_tasks_md,
    parse_feature_folder,
    generate_edison_task,
    sync_speckit_feature,
    SpecKitTask,
    SpecKitFeature,
    SyncResult,
)

# Parse tasks.md content
tasks = parse_tasks_md(content)

# Parse full feature folder
feature = parse_feature_folder(Path("specs/auth/"))

# Generate Edison task
task = generate_edison_task(speckit_task, feature, prefix="auth")

# Sync feature
result = sync_speckit_feature(feature, prefix="auth", create_qa=True)
print(f"Created: {result.created}")
print(f"Updated: {result.updated}")
print(f"Flagged: {result.flagged}")
```
