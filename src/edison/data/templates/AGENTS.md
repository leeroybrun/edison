# AGENTS – Edison Framework Orchestration Hub

This document defines the canonical orchestration rules for all Edison framework projects.

**Purpose**: Establish fail-closed guidelines ensuring every agent follows the same workflow, regardless of project or technology.

---

## Agent Compliance Checklist (Fail-Closed)

Every agent MUST follow these 13 items. **Any violation halts work immediately** until resolved.

1. **Mandatory preload** – Load `.edison/_generated/constitutions/ORCHESTRATOR.md` and every `mandatory` entry before touching code. Edison CLI (`edison session next`, `edison task claim`) injects rules proactively.

2. **Correct intake prompt** – Start every session via `.edison/_generated/constitutions/ORCHESTRATOR.md`. That checklist handles QA sweeps + task selection.

3. **Session record alive** – Every session has a JSON file under `.project/sessions/{active,closing,validated}/`. Keep Owner, Last Active, hierarchy links, and Activity Log current via Edison guarded CLIs.

4. **Work from task files** – Operate exclusively inside `.project/tasks/*` + `.project/qa/*`; keep IDs spaced by ≥50 so follow-ups slot cleanly.

5. **TDD is law** – RED → GREEN → REFACTOR for every change; log the cycle + evidence paths in the task file. No mocked tests - use real filesystem, real git, real processes.

6. **Delegate, don't do** – Route work through `.edison/_generated/constitutions/ORCHESTRATOR.md`; only ≤10-line surgical edits may be performed directly. Complex features go to specialized implementers.

7. **Context7 first** – Query Context7 before coding against any post-training package detected by `context7.triggers` / `context7.contentDetection`. Never guess about post-training APIs.

8. **Automated checks first** – Build, type-check, lint, and test must be green before QA moves to `todo/`. No exceptions.

9. **Validator waves** – Run required validators in batched waves up to the manifest cap; record verdicts + artifact links inside the QA brief. Rejected work stays in `tasks/wip/` with QA back in `qa/waiting/` until revalidated.

10. **Honest status** – Directory names describe truth: `todo` = unstarted, `wip` = active/rejected, `done` = awaiting validation, `validated` = all checks + evidence complete. No status lies in shadow documents.

11. **No shadow summaries** – Track progress only through task files, QA briefs, session records, git history, and validation evidence. Never maintain parallel status in memory or separate docs.

12. **Conventional commits** – `type(scope): description`; stage relevant files only. Use Edison git workflow guidelines.

13. **Fail closed** – Any guardrail breach (preload, Context7, automation, validator availability, session timeout) **halts work until resolved**. When in doubt, stop and ask.

**Enforcement**: Edison guards (CLI transitions) enforce these checks at every transition. Violations block progress.

---

## Mandatory Preload

**Before starting work**, agents MUST load these files (paths relative to project root):

### Framework Guidelines (Always)

- `.edison/_generated/guidelines/SESSION_WORKFLOW.md` - Canonical session lifecycle
- `.edison/_generated/guidelines/HONEST_STATUS.md` - Status integrity rules
- `.edison/_generated/guidelines/VALIDATION.md` - Validator requirements and waves
- `.edison/_generated/guidelines/QUALITY.md` - Code quality standards
- `.edison/_generated/guidelines/TDD.md` - Test-driven development enforcement
- `.edison/_generated/guidelines/CONTEXT7.md` - Post-training package query rules
- `.edison/_generated/guidelines/GIT_WORKFLOW.md` - Git commit and branch patterns
- `.edison/_generated/guidelines/DELEGATION.md` - Delegation patterns and rules
- `.edison/_generated/guidelines/orchestrators/STATE_MACHINE_GUARDS.md` - State transition guards

### Project Configuration (Always)

- `.edison/_generated/constitutions/ORCHESTRATOR.md` - Authoritative preload list (project-specific)
- `.edison/_generated/AVAILABLE_VALIDATORS.md` - Validator roster and triggers (project-specific)
- `.edison/_generated/constitutions/ORCHESTRATOR.md` - Delegation model routing (project-specific)

### Project-Specific Client Rules (Conditional)

Configured in `.edison/_generated/constitutions/ORCHESTRATOR.md` under `mandatory` array. May include:
- Claude-specific rules (`.edison/_generated/constitutions/AGENTS.md`)
- Cursor-specific rules (`.edison/_generated/constitutions/AGENTS.md`)
- Other client packs as needed

**Proactive Loading Mechanism**:

Edison CLI injects rules automatically:
- **On planning**: `edison session next <session> --with-rules`
- **On claim**: `edison task claim <id> --with-rules`
- **On QA creation**: `edison qa new <id> --with-rules`

**Fail-Closed**: If manifest or required configs missing, CLI refuses to proceed.

---

## Quick Navigation

### Guidelines vs Guides (Know the Difference)

**Guidelines** (Condensed, Mandatory)
- Location: `.edison/_generated/guidelines/`
- Purpose: Concise rules for active workflows
- When: Always loaded at session start
- Examples: SESSION_WORKFLOW, TDD, VALIDATION
- Length: Optimized for AI context windows

**Guides** (Deep Dives, On-Demand)
- Location: `.edison/_generated/guidelines/` + `.edison/_generated/guidelines/`
- Purpose: Extended patterns, examples, deep technical explanations
- When: Load only when needed (preserves context budget)
- Examples: TDD_GUIDE (extended), QUALITY_GUIDE (deep patterns)
- Length: Comprehensive references (100-500+ lines)

**Context Discipline Rules**:
- `RULE.CONTEXT.BUDGET_MINIMIZE` - Load only what you actively need
- `RULE.CONTEXT.NO_BIG_FILES` - Don't load large files unnecessarily
- `RULE.CONTEXT.SNIPPET_ONLY` - For delegation, send code snippets not full files
- `RULE.CONTEXT.GUIDES_ON_DEMAND` - Guidelines always, guides conditionally

---

## Rule Registry

Edison guidelines contain **anchored rule IDs** indexed in `.edison/_generated/AVAILABLE_VALIDATORS.md`.

**Discovery**:
```bash
edison rules list
```

**Show rule details**:
```bash
edison rules show <RULE_ID>
```

**Require rule in prompt** (outputs wrapped snippet for agent consumption):
```bash
edison rules require <RULE_ID>
```

**Orchestrators MUST** load every rule ID referenced by `edison session next`.

---

## Session Workflow

See `.edison/_generated/guidelines/SESSION_WORKFLOW.md` for the canonical lifecycle specification.

**Key Phases**:
1. **Session Intake** (via ORCHESTRATOR.md constitution checklist)
2. **Task Claiming** (moves files to session scope)
3. **Implementation** (TDD cycle with evidence logging)
4. **Validation** (automated checks + validator waves)
5. **QA** (multi-round validation until approved)
6. **Session Completion** (transactional restore to global queues)

**Session Timeout**: Sessions expire after `session.timeout_hours` (default 8). Use `edison session track heartbeat --task <task-id>` to update activity timestamp. Expired sessions cannot claim new tasks (fail-closed).

---

## Task, QA, and Session Directory Structure

```plaintext
.project/
  tasks/
    todo/       - Unclaimed tasks waiting for implementer
    wip/        - Active implementation OR rejected work
    done/       - Implementation complete, awaiting validation
    validated/  - All required validators passed
    
  qa/
    waiting/    - QA brief created, task not done yet
    todo/       - Task done, ready for validator execution
    wip/        - Validation in progress
    done/       - All validators passed
    validated/  - Final approval (matches task validated)
    
  sessions/
    wip/        - Active sessions (semantic state: active)
    done/       - Closing / post-timeout cleanup (semantic state: closing)
    validated/  - Completed and archived sessions
```

**Honest Status Principle**: Directory name = source of truth. No status lies in comments, summaries, or shadow tracking.

**Session Isolation**: When task claimed into session, file physically moves to `.project/sessions/wip/<session-id>/tasks/`. Prevents cross-session interference.

---

## Orchestration Model (Summary)

### Backlog Management
- Tasks numbered with gaps (≥50) for follow-up insertion
- Parent-child hierarchy for complex features
- Task splitting for parallel implementation

### Concurrency
- Edison supports multiple parallel sessions
- Configure limits in `edison.yaml` or manifest
- Session-scoped queues prevent race conditions

### Delegation
- Route complex work through `.edison/_generated/constitutions/ORCHESTRATOR.md`
- Match file patterns to model capabilities
- Specialized implementers for frontend/backend/database/testing

### Sub-Agent Behavior
- **Never re-delegate**: Sub-agents implement directly or report blockers
- **Context discipline**: Send snippets, not full files
- **Evidence logging**: Record all actions in task file
- **Zen MCP integration**: Record `continuation_id` for conversation continuity

### Validator Orchestration
- Validators execute in **waves** (batched by manifest cap)
- Blocking validators must pass (security, performance, etc.)
- Non-blocking validators create follow-up tasks
- Bundle validation for parent+children clusters

---

## References

### Core Configuration

**Framework Defaults**:
- `.edison/_generated/constitutions/ORCHESTRATOR.md` - Framework orchestration

**Project Overlay**:
- `edison.yaml` - Project-specific configuration overrides
- `.edison/_generated/constitutions/ORCHESTRATOR.md` - Authoritative preload list

**State Machine**:
- `.edison/_generated/STATE_MACHINE.md` - State definitions and transitions
- `.edison/_generated/guidelines/orchestrators/STATE_MACHINE_GUARDS.md` - Guard enforcement rules

### Guidelines (Mandatory Reading)

All in `.edison/_generated/guidelines/`:
- `SESSION_WORKFLOW.md` - Canonical session lifecycle
- `DELEGATION.md` + `.edison/_generated/constitutions/ORCHESTRATOR.md` - Delegation routing
- `TDD.md` - Test-driven development enforcement (RED→GREEN→REFACTOR)
- `QUALITY.md` - Code quality standards and patterns
- `HONEST_STATUS.md` - Status integrity and directory-name truth
- `VALIDATION.md` - Validator requirements, waves, and bundle validation
- `CONTEXT7.md` - Post-training package query requirements
- `GIT_WORKFLOW.md` - Git commit conventions and workflow
- `STATE_MACHINE_GUARDS.md` - State transition validation

### Templates

**Task/QA Structure**:
- `.edison/_generated/documents/TASK.md` - Composed task document template (used by `edison task new`)
- `.edison/_generated/documents/QA.md` - Composed QA document template (used by `edison qa new`)

**Session Templates**:
- `.edison/_generated/STATE_MACHINE.md` - State machine definitions
- `.edison/_generated/constitutions/ORCHESTRATOR.md` - Session intake checklist

### CLI Reference (Automation)

**Session Lifecycle**:
- `edison session` - Session management CLI (new, status, complete, etc.)
- `edison session next` - Action planning and task recommendation
- `edison session verify` - Guard validation

**Task Operations**:
- `edison task claim` - Claim task into session (moves file)
- `edison task status` - Check task state
- `edison task ready` - Mark task done (triggers validation)
- `edison task split` - Create child tasks for parallel work
- `edison task link` - Link parent-child relationships

**QA Operations**:
- `edison qa new` - Create QA brief for task
- `edison qa round` - Create new validation round
- `edison qa promote` - Move QA through states (validated, etc.)
- `edison qa bundle` - Bundle validation for parent+children

**Validator Orchestration**:
- `edison qa validate <task-id> --session <session-id> --execute` - Execute validator waves (batched, respects wave config)
- `edison qa validate` - Aggregate validator verdicts

**Delegation**:
- `edison delegation validate` - Validate delegation config schema

---

## Session Isolation (Mandatory)

**Core Principle**: When claiming a task into an active session, the file **physically moves** under `.project/sessions/wip/<session-id>/`.

**Why Physical Movement**:
- Prevents race conditions (two sessions can't claim same task)
- Clear ownership (file location = claimed by session)
- Atomic operations (move = claim in one operation)
- Transactional restore (on completion, move back to global)

**Session-Scoped Queues**:
```plaintext
.project/sessions/wip/<session-id>/
  tasks/
    wip/      - Tasks claimed by this session
    done/     - Tasks completed, awaiting validation
  qa/
    wip/      - QA in progress for this session
```

**Global Queues** (unclaimed work only):
```plaintext
.project/
  tasks/todo/     - Available for any session to claim
  tasks/validated/ - Completed work (no longer session-scoped)
```

**Rules**:
- Always operate on **session-scoped queues** (files in session directory)
- Global queues contain **only unclaimed work**
- Use `--session <id>` flag or set `{PROJECT_NAME}_OWNER` env var
- On completion, files **restore to global queues** transactionally

**Fail-Closed**: If restore fails (e.g., permission error), session remains in `closing` state until manually repaired via recovery scripts.

---

## Parallel Implementation Pattern

For large tasks requiring multiple implementers working simultaneously:

### Step 1: Split Task

```bash
edison task split <parent-task-id> --children 3
```

Creates:
- Parent task remains as meta-coordinator
- Child tasks (e.g., task-105, task-110, task-115) for parallel work

### Step 2: Assign Children

Each implementer claims one child task into their own session:

```bash
# Implementer A
edison task claim 105 --session session-a

# Implementer B
edison task claim 110 --session session-b

# Implementer C
edison task claim 115 --session session-c
```

### Step 3: Implement in Parallel

Each follows standard workflow:
- TDD cycle (RED → GREEN → REFACTOR)
- Automated checks (build, type-check, lint, test)
- Mark done when complete

### Step 4: Bundle Validation

Parent task coordinates validation:

```bash
edison qa validate <parent-task-id> --session <session-id> --execute
```

Runs validators on **entire cluster** (parent + all children).

### Step 5: Complete Session

Once bundle validated, each implementer completes their session.

**Parent Task Role**:
- Meta-coordinator (no direct code changes)
- Defines overall feature scope
- Tracks child task completion
- Triggers bundle validation
- Creates integration task if needed

**Child Task Role**:
- Independent implementation unit
- Can be worked on concurrently
- Follows full TDD + validation workflow
- Evidence logged in own task file

See `.edison/_generated/guidelines/SESSION_WORKFLOW.md` section "Parallel Sessions and Task Splitting" for detailed workflow.

---

## Project-Specific Extensions

This template provides the Edison framework orchestration hub. **Projects extend via additional includes**:

### Example: Project Overlay

`.edison/_generated/constitutions/AGENTS.md` structure:
```markdown
\{\{include:.edison/_generated/constitutions/AGENTS.md\}\}
{{include:.edison/_generated/constitutions/AGENTS.md}}
```

Project overlay adds:
- Project-specific tech stack
- Deployment notes
- Patterns and conventions
- Post-training package versions

**Principle**: Edison template = project-agnostic rules. Project overlay = specific context.

---

## Fail-Closed Philosophy

Edison framework is **fail-closed by design**. When something is wrong, **work stops** until fixed:

**Fail-Closed Scenarios**:
- Session expired → Cannot claim new tasks
- Mandatory config missing → Scripts refuse to run
- Validator unavailable → Validation blocked
- TDD evidence missing → Cannot mark done
- Automation failing → Cannot proceed to QA
- Guard violation → State transition blocked

**Why Fail-Closed**:
- Prevents cascading errors
- Forces explicit fixing of root causes
- Maintains system integrity
- Ensures evidence trail completeness

**Recovery**:
- Edison CLI provides recovery commands
- Session timeout: `edison session recovery repair-session`
- Lock contention: `edison session recovery clear-locks`
- Orphaned worktrees: `edison session recovery clean-worktrees`

**Never bypass guardrails**. If blocked, fix the underlying issue.

---

## Summary

This orchestration hub ensures:
- ✅ Consistent workflow across all agents and projects
- ✅ Fail-closed enforcement at every transition
- ✅ Complete evidence trail (task files, QA briefs, session records)
- ✅ TDD discipline (RED → GREEN → REFACTOR mandatory)
- ✅ Quality gates (automated checks + validator waves)
- ✅ Session isolation (prevents concurrent interference)
- ✅ Delegation patterns (route complex work to specialists)
- ✅ Post-training safety (Context7 queries mandatory)

**Next Step**: Read `.edison/_generated/constitutions/ORCHESTRATOR.md` to begin a session correctly.
