<!-- TaskID: 2024-wdoc-004-multiple-start-prompts -->
<!-- Priority: 2024 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: feature -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave1-groupC -->
<!-- EstimatedHours: 3 -->

# WDOC-004: Create Multiple START Prompt Architecture

## Summary
Design and implement multiple START prompts for different session purposes instead of one monolithic START.SESSION.md.

## Problem Statement
The old START.SESSION.md tried to handle multiple scenarios:
- Starting fresh session
- Reclaiming stale tasks
- Auto-continuing work
- Cleanup operations

This should be split into purpose-specific START prompts.

## Dependencies
- None

## Objectives
- [x] Design START prompt architecture
- [x] Create START_NEW_SESSION.md
- [x] Create START_CONTINUE_STALE.md
- [x] Create START_AUTO_NEXT.md
- [x] Create START_CLEANUP.md
- [x] Update composition to generate these

## Source Files

### Current Start File
```
/Users/leeroy/Documents/Development/edison/src/edison/data/start/
```

### Output Locations
```
/Users/leeroy/Documents/Development/edison/src/edison/data/start/
├── START_NEW_SESSION.md
├── START_CONTINUE_STALE.md
├── START_AUTO_NEXT.md
└── START_CLEANUP.md
```

## Precise Instructions

### Step 1: Design Architecture

```markdown
## START Prompt Architecture

### START_NEW_SESSION
**Purpose**: Begin a fresh work session
**When used**: User starts a new coding session
**Behavior**:
1. Load orchestrator constitution
2. Load mandatory reads
3. Display session status
4. Wait for user direction (what to work on)

### START_CONTINUE_STALE
**Purpose**: Reclaim and continue stale tasks
**When used**: Tasks have been idle >4h
**Behavior**:
1. Find stale tasks in wip
2. Display stale task list
3. Ask user which to reclaim
4. Continue work on selected tasks

### START_AUTO_NEXT
**Purpose**: Automatically pick and start next tasks
**When used**: User wants hands-off task selection
**Behavior**:
1. Find ready tasks in todo
2. Identify parallelizable tasks
3. Create session and claim tasks
4. Begin work immediately

### START_CLEANUP
**Purpose**: Clean up stale sessions and tasks
**When used**: Project needs tidying
**Behavior**:
1. Find all stale tasks
2. Move back to todo with notation
3. Archive stale sessions
4. Report cleanup results
```

### Step 2: Create START_NEW_SESSION.md

```markdown
# START_NEW_SESSION

You are starting a fresh work session as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATORS.md`

2. **Load Mandatory Reads**
   See constitution for mandatory file list.

3. **Display Status**
   Run: `edison session status`
   Run: `edison task status`

4. **Report to User**
   Present:
   - Current session status (if any)
   - Tasks in progress (if any)
   - Ready tasks available
   - Any stale items requiring attention

5. **Await Direction**
   Ask user:
   - "What would you like to work on?"
   - Present options based on status

## DO NOT automatically:
- Claim tasks without user approval
- Continue stale work without asking
- Make assumptions about priority

## Key Commands
```bash
edison session start         # Start new session
edison session status        # Check session status
edison task ready            # List ready tasks
edison task claim <id>       # Claim a task
```
```

### Step 3: Create START_CONTINUE_STALE.md

```markdown
# START_CONTINUE_STALE

You are reclaiming stale tasks as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATORS.md`

2. **Find Stale Tasks**
   Run: `edison session stale --list`
   (Tasks idle >4 hours)

3. **Present Stale Tasks**
   For each stale task, show:
   - Task ID and title
   - Last activity timestamp
   - Current progress/status
   - Any blockers noted

4. **Reclaim with User Approval**
   For each task user wants to continue:
   Run: `edison task reclaim <task-id>`

5. **Continue Work**
   Resume task workflow from current state.

## Key Commands
```bash
edison session stale --list  # List stale tasks
edison task reclaim <id>     # Reclaim stale task
edison session resume <id>   # Resume stale session
```
```

### Step 4: Create START_AUTO_NEXT.md

```markdown
# START_AUTO_NEXT

You are auto-starting work as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATORS.md`

2. **Find Ready Tasks**
   Run: `edison task ready --json`

3. **Analyze Parallelization**
   Identify tasks that can run in parallel:
   - No dependencies on each other
   - Different file scopes
   - Different agent types

4. **Create Session and Claim**
   Run: `edison session start --auto`
   Run: `edison task claim <task-id>` for each selected task

5. **Begin Work**
   Start implementation immediately.
   Delegate to sub-agents as needed.

## Selection Priority
1. P1 (Critical) tasks first
2. Tasks with no blockers
3. Tasks matching available agents
4. Smaller tasks for quick wins

## Key Commands
```bash
edison task ready --json     # Get ready tasks as JSON
edison session start --auto  # Start session with auto-select
edison task claim <id>       # Claim tasks
```
```

### Step 5: Create START_CLEANUP.md

```markdown
# START_CLEANUP

You are cleaning up the project as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATORS.md`

2. **Identify Stale Items**
   Run: `edison session stale --list`
   Run: `edison task stale --list`

3. **Present Cleanup Plan**
   Show user:
   - Stale sessions to archive
   - Stale tasks to move back to todo
   - QA items requiring attention

4. **Execute with Approval**
   For each stale task:
   ```bash
   edison task reset <task-id> --reason="Stale: moved back to todo"
   ```

   For each stale session:
   ```bash
   edison session archive <session-id>
   ```

5. **Report Results**
   Summarize:
   - Tasks reset
   - Sessions archived
   - Any items needing manual attention

## DO NOT delete any work
- Always preserve history
- Add notes to reset tasks
- Archive, never delete sessions

## Key Commands
```bash
edison task reset <id>       # Move task back to todo
edison session archive <id>  # Archive stale session
edison project cleanup       # Full cleanup (if implemented)
```
```

### Step 6: Update Composition

Add start prompts to composition:

```yaml
# In composition.yaml
types:
  start:
    mode: simple_copy
    sources:
      - core: src/edison/data/start/
    output: _generated/start/
```

## Verification Checklist
- [ ] START_NEW_SESSION.md created
- [ ] START_CONTINUE_STALE.md created
- [ ] START_AUTO_NEXT.md created
- [ ] START_CLEANUP.md created
- [ ] Each prompt has clear purpose
- [ ] Each prompt loads constitution first
- [ ] Commands are correct Edison CLI
- [ ] Prompts are composable

## Success Criteria
Four distinct START prompts exist, each serving a specific session initiation purpose.

## Related Issues
- Audit ID: Q-011
- Audit ID: CG-023
