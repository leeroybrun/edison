# Edison Roles

## Overview

Edison uses **three distinct roles**, each with its own constitution, guidelines, and CLI command access. This separation of concerns ensures quality through independent validation and clear responsibilities.

**The Three Roles:**
1. **Orchestrator** - Coordinates work, delegates tasks, manages sessions
2. **Agent** (Implementer) - Implements features, fixes bugs, writes code
3. **Validator** - Reviews code, validates implementations, ensures quality

Each role has:
- A dedicated constitution file (read via `edison read <ROLE> --type constitutions`)
- Mandatory reading materials specific to their responsibilities
- Restricted CLI command access (fail-closed by design)
- Clear boundaries of what they can and cannot do

---

## 1. Orchestrator Role

### Purpose
Coordinate work, delegate tasks to specialized agents, manage session lifecycle, and orchestrate validation.

### Constitution
Run `edison read ORCHESTRATOR --type constitutions`.

### Mandatory Reads
Orchestrators MUST read these files at session start:
- **SESSION_WORKFLOW.md** - Complete workflow for managing active sessions
- **DELEGATION.md** - Delegation priority chain and agent selection rules
- **AVAILABLE_AGENTS.md** - Current agent roster with specializations
- **AVAILABLE_VALIDATORS.md** - Validator roster with trigger patterns and blocking status
- **TDD.md** - Test-Driven Development requirements
- **VALIDATION.md** - Validation workflow and independence rules

### Allowed Commands

#### Session Management
```bash
edison session create [--session-id <id>]     # Create new session (ID auto-infers if omitted)
edison session start <task-id>         # Start session with orchestrator
edison session status <session-id>     # Check session state
edison session next <session-id>       # Get next recommended actions (CRITICAL)
edison session close <session-id>      # Close completed session
edison session verify --phase closing  # Verify session ready for closing
edison session sync-git <session-id>   # Sync git worktree
```

#### Task Management
```bash
edison task claim <task-id> --session <id>   # Claim task into session
edison task status <task-id>                 # Check task state
edison task ready <task-id>                  # Promote task to done
edison task list                             # List tasks
edison task link <parent> <child>            # Link parent/child tasks
edison task split <task-id>                  # Split task into subtasks
```

#### QA Management
```bash
edison qa new <task-id> --session <id>   # Create QA brief
edison qa promote --task <id> --to <state>   # Promote QA state
edison qa bundle <task-id>                   # Create validation bundle
```

#### Configuration and Composition
```bash
edison config <subcommand>     # Configuration management
edison compose <subcommand>    # Compose constitutions/guidelines
```

### Responsibilities

**Core Duties:**
1. **Session Management**
   - Start and manage session lifecycle
   - Keep session record alive (update every 2 hours)
   - Work in isolated session worktree
   - Log milestones in Activity Log

2. **Task Coordination**
   - Claim tasks from global queue into session
   - Ensure QA brief is paired when task enters `wip`
   - Track task dependencies (parent/child relationships)
   - Handle task state transitions via guarded CLIs

3. **Delegation**
   - Delegate implementation to specialized agents
   - Follow delegation priority chain:
     1. User instruction (highest priority)
     2. File pattern matching
     3. Task type
     4. Default fallback
   - Never implement directly (except trivial tasks)
   - Monitor sub-agent progress

4. **Validation Orchestration**
   - Launch ALL blocking validators independently
   - Never validate own implementation
   - Wait for ALL blocking validators to complete
   - Aggregate verdicts and make approval decision
   - Handle rejections by creating follow-up tasks

5. **Quality Gates**
  - Run `edison task waves` to pick parallel work (Wave 1), then `edison task ready` before validation
   - Verify TDD evidence exists
   - Check automation evidence (type-check, lint, test, build)
   - Ensure child tasks are ready before promoting parent

6. **Session Closure**
   - Verify all tasks are `validated`
   - Verify all QA briefs are `done` or `validated`
   - Run verification checks
   - Close session only when all work complete

**Workflow Loop:**
```
1. edison session next <session-id>     # Get recommended actions
2. Read output (rules → actions → delegation)
3. Execute recommended command
4. REPEAT from step 1
```

### What Orchestrators Must NOT Do

**FORBIDDEN:**
- ❌ Implement code directly (delegate to agents instead)
- ❌ Self-validate their work (independence violation)
- ❌ Skip validation steps (fail-closed enforcement)
- ❌ Move files manually (use guarded CLIs only)
- ❌ Skip state transitions (adjacent states only)
- ❌ Close sessions with blockers or unvalidated work
- ❌ Validate using same model as implementation

---

## 2. Agent Role (Implementer)

### Purpose
Implement features, fix bugs, write code following TDD practices.

### Constitution
Run `edison read AGENTS --type constitutions`.

### Mandatory Reads
Agents MUST read these files before implementation:
- **AGENT_GUIDELINES.md** - Core guidelines for all agents
- **MANDATORY_WORKFLOW.md** - Required workflow steps
- **OUTPUT_FORMAT.md** - Implementation report format
- **TDD.md** - Red→Green→Refactor cycle requirements
- **CONTEXT7.md** - How to use Context7 MCP for post-training packages

### Allowed Commands

#### Implementation Tracking
```bash
edison session track start --task <id> --type implementation   # Start implementation
edison session track complete --task <id>                      # Mark complete
```

#### Task Status (Read-Only)
```bash
edison task status <task-id>    # Check task details
```

#### Git Commands
```bash
git add <files>       # Stage changes
git commit -m "msg"   # Commit with message
git diff              # View changes
git status            # Check status
# All standard git commands for implementation
```

#### Context7 MCP (Documentation)
```
mcp__context7__resolve-library-id     # Resolve library ID
mcp__context7__get-library-docs       # Fetch documentation
```

### Responsibilities

**Core Duties:**
1. **Follow TDD Strictly**
   - Write failing test FIRST (RED)
   - Implement code to pass test (GREEN)
   - Refactor for quality (REFACTOR)
   - Never skip this cycle

2. **Use Context7 for Post-Training Packages**
   - Query Context7 BEFORE coding
   - Use current documentation, not outdated info
   - Store Context7 markers in evidence directory
   - Ensure HMAC stamping when enabled

3. **Track Work with Heartbeats**
   - Call `edison session track start` at beginning
   - Work on implementation
   - Call `edison session track complete` when done
   - Keep tracking stamps accurate

4. **Create Implementation Reports**
   - Document changes made
   - List files modified
   - Include test evidence
   - Report blockers honestly
   - Suggest follow-up tasks if needed

5. **Run Automation Suite**
   - Type-check: `npm run type-check` (or project equivalent)
   - Lint: `npm run lint`
   - Test: `npm run test`
   - Build: `npm run build`
   - Capture outputs in evidence directory

6. **Report Completion Clearly**
   - Tell orchestrator when done
   - Provide evidence paths
   - Mention any blockers encountered
   - Suggest next steps

### What Agents Must NOT Do

**FORBIDDEN:**
- ❌ Claim tasks (orchestrator does this)
- ❌ Run validators (validator role only)
- ❌ Promote task states (orchestrator decides)
- ❌ Re-delegate to other agents (orchestrator manages delegation)
- ❌ Skip TDD cycle (strict requirement)
- ❌ Self-validate implementation (independence violation)
- ❌ Manage sessions (orchestrator responsibility)
- ❌ Skip automation checks (required evidence)

---

## 3. Validator Role

### Purpose
Review code, validate implementations, ensure quality through independent assessment.

### Constitution
Run `edison read VALIDATORS --type constitutions`.

### Mandatory Reads
Validators MUST read these files before validation:
- **VALIDATOR_GUIDELINES.md** - Core validator guidelines
- **VALIDATOR_WORKFLOW.md** - Complete validation workflow
- **OUTPUT_FORMAT.md** - JSON report format requirements
- **CONTEXT7.md** - Context7 usage for validators

### Allowed Commands

#### Validation Commands
```bash
edison qa validate <task-id> [--round N]                 # Validate task
edison qa validate <task-id> --session <session-id>      # Bundle validation
edison qa bundle <task-id>                               # Inspect bundle
edison qa round <task-id> --current                      # Show current round
edison qa round <task-id> --list                         # List round history + evidence dirs
edison qa round <task-id> --status <status>              # Append round status (does not create evidence dir unless --new)
```

#### Read-Only Commands
```bash
edison task status <task-id>     # Check task state
edison qa status                 # Check QA state
```

### Responsibilities

**Core Duties:**
1. **Review Implementation Against Requirements**
   - Load QA brief and acceptance criteria
   - Review implementation report
   - Examine git diff for changes
   - Check evidence files

2. **Check TDD Compliance**
   - Verify test-first approach
   - Check test coverage
   - Validate test quality (not just coverage numbers)
   - Ensure no mocks on critical paths

3. **Verify Context7 Usage**
   - Check Context7 markers exist for post-training packages
   - Verify HMAC stamps when enabled
   - Ensure current documentation was used

4. **Produce Structured Validation Reports (JSON)**
   - Location: `.project/qa/validation-evidence/<task-id>/round-N/<validator-name>.json`
   - Required fields: validator, task_id, round, timestamp, status, model, continuationId, issues, summary, metrics
   - Issue severities: blocking, warning, advisory

5. **Identify Blocking vs Advisory Issues**
   - **Blocking**: Must be fixed before promotion (security, critical bugs, missing tests)
   - **Warning**: Should be fixed, not blocking (code quality, minor issues)
   - **Advisory**: Nice to have, optional (style suggestions, optimizations)

6. **Suggest Follow-Up Tasks**
   - Identify work discovered during validation
   - Suggest improvements beyond current scope
   - Link to parent task for traceability

7. **Determine Verdict**
   - **approve**: All checks pass, ready for promotion
   - **reject**: Blocking issues found, requires fixes
   - **blocked**: Missing evidence, cannot validate

### Validator Types

#### Global Validators (Always Run, Blocking)
- **global-codex**: Codex model perspective, code quality and TDD compliance
- **global-claude**: Claude model perspective, architecture and patterns
- **global-gemini**: Gemini model perspective, alternative perspectives (advisory)

#### Critical Validators (Always Run, Blocking)
- **security**: OWASP Top 10, auth, input validation, secrets exposure
- **performance**: Bundle size, query efficiency, caching, N+1 detection

#### Specialized Validators (Triggered by File Patterns)
Defined in active packs, check `AVAILABLE_VALIDATORS.md` for current roster:
- **api**: REST/API patterns (triggers on API file patterns)
- **testing**: Test quality (triggers on test file patterns)
- **database**: Schema design (triggers on database file patterns)
- **ui-framework**: Component patterns (triggers on UI file patterns)
- **frontend-framework**: Framework patterns (triggers on framework file patterns)

### What Validators Must NOT Do

**FORBIDDEN:**
- ❌ Fix code directly (create follow-up tasks instead)
- ❌ Promote tasks (orchestrator does this after validation)
- ❌ Manage sessions (orchestrator responsibility)
- ❌ Implement features (agent responsibility)
- ❌ Validate own implementation (independence violation)
- ❌ Skip required checks (fail-closed enforcement)
- ❌ Modify task/QA files (read-only access)

---

## 4. Role Determination

### How LLMs Determine Their Role

**Entry Point**: All LLMs read `AGENTS.md` (root file) which directs them to:

1. **Determine context** - Are they starting a session, implementing a task, or validating?
2. **Read appropriate constitution** - Based on context, load the correct constitution:
   - Orchestrator: `edison read ORCHESTRATOR --type constitutions`
   - Agent: `edison read AGENTS --type constitutions`
   - Validator: `edison read VALIDATORS --type constitutions`
3. **Load mandatory reads** - Each constitution lists required reading materials
4. **Follow role-specific workflow** - Execute according to role responsibilities

### Constitution Auto-Generation

Constitutions are **auto-generated** from configuration layers:
```bash
edison compose --all    # Regenerate all constitutions
```

**Source Layers** (overlaid in order):
1. Core framework defaults
2. Pack-specific additions
3. Project-specific overrides

**Output**: `edison read <ROLE> --type constitutions`

---

## 5. Multi-Model Validation

Edison uses **multiple LLM models as validators** to achieve consensus and catch blind spots.

### Validator Models

**Global Validators** (run on every task):
- **Codex Model** (global-codex) - Code quality, TDD, security basics
- **Claude Model** (global-claude) - Architecture, patterns, best practices
- **Gemini Model** (global-gemini) - Alternative perspectives, edge cases (advisory)

### Consensus Requirement

**ALL blocking validators MUST approve** for task to pass validation:
- If **ANY** blocking validator rejects → task is **REJECTED**
- If **ALL** blocking validators approve → task is **APPROVED**
- If **ANY** blocking validator is blocked → task is **BLOCKED** (fix and re-run)

**Advisory validators** provide feedback but don't block approval.

### Independence Enforcement

**CRITICAL**: Validators MUST be independent from implementation:
- Different model than implementation (when possible)
- Never validate own work
- Launched independently via orchestrator
- No coordination between validators (independent judgments)

**Rationale**: Independent validation catches blind spots and confirmation bias.

---

## 6. Separation of Concerns

### Clear Boundaries

| Concern | Orchestrator | Agent | Validator |
|---------|-------------|-------|-----------|
| **WHAT to do** | ✅ Decides | ❌ | ❌ |
| **WHO does it** | ✅ Assigns | ❌ | ❌ |
| **HOW to implement** | ❌ | ✅ Implements | ❌ |
| **WHETHER it's correct** | ❌ | ❌ | ✅ Validates |

### Workflow Flow

```
┌─────────────────┐
│  Orchestrator   │  1. Claim task
│                 │  2. Create QA brief
└────────┬────────┘  3. Delegate to agent
         │
         ↓
┌─────────────────┐
│     Agent       │  4. Implement (TDD)
│  (Implementer)  │  5. Run automation
└────────┬────────┘  6. Create report
         │
         ↓
┌─────────────────┐
│  Orchestrator   │  7. Launch validators
│                 │  8. Monitor progress
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Validators    │  9. Review independently
│  (Multiple)     │  10. Generate reports
└────────┬────────┘  11. Determine verdict
         │
         ↓
┌─────────────────┐
│  Orchestrator   │  12. Aggregate verdicts
│                 │  13. Approve OR reject
└─────────────────┘  14. Close session OR create follow-ups
```

### Command Access Matrix

| Command Category | Orchestrator | Agent | Validator |
|-----------------|--------------|-------|-----------|
| Session management | ✅ | ❌ | ❌ |
| Task claiming | ✅ | ❌ | ❌ |
| Task status (read) | ✅ | ✅ | ✅ |
| Implementation tracking | ❌ | ✅ | ❌ |
| Git commands | ✅ | ✅ | ❌ |
| QA promotion | ✅ | ❌ | ❌ |
| Validation execution | ❌ | ❌ | ✅ |
| Bundle inspection | ✅ | ❌ | ✅ |
| Context7 MCP | ✅ | ✅ | ✅ |

---

## 7. Practical Examples

### Example 1: New Feature Implementation

**Orchestrator** (Session Owner):
```bash
# 1. Create session
edison session create --session-id sess-001

# 2. Claim task
edison task claim TASK-123 --session sess-001

# 3. Create QA brief
edison qa new TASK-123 --session sess-001

# 4. Get delegation recommendation
edison session next sess-001
# Output: "Suggest: component-builder-nextjs based on file pattern *.tsx"

# 5. Delegate to agent (via Task tool or agent invocation)
# Agent implements feature...

# 6. After agent completes, promote task
edison task ready TASK-123 --session sess-001

# 7. Start validation
edison qa promote --task TASK-123 --to todo

# 8. Launch validators (via delegation)
# Validators review independently...

# 9. After all validators approve, promote QA
edison qa promote --task TASK-123 --to validated

# 10. Close session
edison session close sess-001
```

**Agent** (Implementer):
```bash
# 1. Start tracking
edison session track start --task TASK-123 --type implementation

# 2. Query Context7 for current docs
# (use MCP tools for library documentation)

# 3. Implement feature (TDD)
# - Write failing test (RED)
# - Implement feature (GREEN)
# - Refactor (REFACTOR)

# 4. Run automation suite
npm run type-check > evidence/command-type-check.txt
npm run lint > evidence/command-lint.txt
npm run test > evidence/command-test.txt
npm run build > evidence/command-build.txt

# 5. Complete tracking
edison session track complete --task TASK-123

# 6. Report to orchestrator
# "Implementation complete. Ready for validation."
```

**Validator** (Code Reviewer):
```bash
# 1. Inspect bundle
edison qa bundle TASK-123

# 2. Run validation
edison qa validate TASK-123

# 3. Review evidence
# - Load QA brief
# - Read implementation report
# - Examine git diff
# - Check automation outputs

# 4. Generate validation report (JSON)
# - Write to evidence directory
# - Include verdict, issues, summary

# 5. If approved:
edison qa round TASK-123 --status approve

# 6. If rejected:
edison qa round TASK-123 --status reject
# (List blocking issues in report)
```

### Example 2: Rejection and Follow-Up

**Orchestrator** handles rejection:
```bash
# 1. Security validator rejects
# Read validator report, identify blocking issues

# 2. Create follow-up task
edison task new --parent TASK-123 --title "Add rate limiting"

# 3. Link to parent
edison task link TASK-123 TASK-124

# 4. Claim follow-up into session
edison task claim TASK-124 --session sess-001

# 5. Create QA brief for follow-up
edison qa new TASK-124 --session sess-001

# 6. Move parent QA back to waiting
edison qa promote --task TASK-123 --to waiting

# 7. Delegate follow-up to agent
# Agent fixes issue...

# 8. After fix complete, re-validate (Round 2)
edison qa promote --task TASK-123 --to todo
# Launch validators again...

# 9. After approval, promote both tasks
edison task ready TASK-124
edison task ready TASK-123
edison qa promote --task TASK-124 --to validated
edison qa promote --task TASK-123 --to validated
```

---

## 8. Key Principles

### Independence
- Validators MUST be independent from implementation
- Never validate own work
- Use different models when possible
- No coordination between validators

### Fail-Closed Enforcement
- All state transitions via guarded CLIs
- Manual file moves are forbidden
- Commands enforce preconditions
- Missing evidence blocks progression

### Context Budget
- Orchestrators: ~50K tokens max
- Use focused snippets (80-120 lines)
- Avoid loading large files
- Extract minimal relevant portions

### Session Isolation
- Sessions operate in isolated worktrees
- Session-scoped tasks under `.project/sessions/wip/<id>/tasks/`
- Never touch other sessions' files
- Restore session-scoped files to global queues on completion

### Honest Status
- Keep task status accurate
- Log blockers immediately
- Report findings honestly
- Never skip steps to "make it pass"

---

## 9. Summary Table

| Aspect | Orchestrator | Agent | Validator |
|--------|-------------|-------|-----------|
| **Primary Focus** | Coordination | Implementation | Quality Assurance |
| **Key Verb** | Delegate | Build | Validate |
| **Constitution** | ORCHESTRATOR.md | AGENTS.md | VALIDATORS.md |
| **Can Implement?** | No (delegate) | Yes (TDD) | No (report only) |
| **Can Validate?** | No (delegate) | No (never self) | Yes (independent) |
| **Can Manage Sessions?** | Yes | No | No |
| **CLI Access** | Full orchestration | Limited implementation | Limited validation |
| **Independence** | N/A | N/A | CRITICAL |
| **Multi-Model?** | No (single orchestrator) | No (single implementer) | Yes (multiple validators) |
| **Blocking Status** | N/A | N/A | Global/Critical: Yes, Specialized: Config-driven |

---

## 10. When You Read This File

**If you are starting work:**
1. Determine your role based on context
2. Read your constitution file
3. Load all mandatory reads
4. Follow your role's workflow
5. Respect boundaries (don't do what your role forbids)

**If you are mid-session:**
1. Re-read your constitution after context compaction
2. Verify you're following role-specific guidelines
3. Use `edison session next` (orchestrators only)
4. Stay within your role's command access

**If you are unsure:**
1. Check the constitution for your role
2. Review mandatory reads
3. Ask the user or orchestrator for clarification
4. Default to fail-closed (don't proceed if uncertain)

---

**This document provides the complete role system architecture. Every LLM working in Edison should understand these roles, their boundaries, and their responsibilities.**
