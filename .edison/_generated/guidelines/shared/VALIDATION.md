# Validation (Core)

Run after implementation is complete and before a task can advance beyond `done/`. QA briefs are the canonical validation record.

## Validation Checklist (fail-closed)
- Build the triggered validator roster from the merged `validation.validators` config (core → packs → project) and the task/session file context (git diff + primary files).
- Automation passing for the round (type-check, lint, test, build or project equivalent).
- QA brief exists in `qa/{waiting|todo|wip}` with roster, commands, expected results, and evidence links; never duplicate QA files.
- Bundle manifest generated before launching validators (see Bundle section).
- Context7 refreshed for every Context7-detected package; add `context7-<pkg>.txt` markers per package in the round evidence directory.
- Required validators launched in waves up to the concurrency cap; record the model used.
- If any blocking validator rejects → task stays in `wip`, QA returns to `waiting`, follow-ups created.
- If any validator is blocked or missing, halt and resolve before proceeding.

## Validator Roster & Waves
To inspect the computed roster for a task (including triggered validators and wave membership), run:

```bash
edison qa validate <task-id> --session <session-id> --dry-run
```

**Global (blocking):** all global validators in the roster always run first and must approve.
**Critical (blocking):** every critical validator in the roster is blocking for promotion.
**Specialized (triggered, blocking if `blocksOnFail=true`):** driven by file triggers in `.edison/_generated/AVAILABLE_VALIDATORS.md`; the active set is listed in `AVAILABLE_VALIDATORS.md`.
**Specialized (triggered, blocking if `blocking=true`):** driven by validator `triggers` patterns in merged config and the task/session file context.

Wave order (mandatory): Global → Critical → Specialized (triggered). Launch in parallel per wave up to the configured cap; batch overflow.

## Batched Parallel Execution Model

Validators run in waves for efficiency and fast feedback:

### Wave Execution Order

```
┌─────────────────────────────────────────────────────────────┐
│ Wave 1: Global Validators (Parallel)                        │
│ ┌─────────────────┐  ┌─────────────────┐                   │
│ │ global-codex    │  │ global-claude   │  → Consensus      │
│ └─────────────────┘  └─────────────────┘    Required       │
└─────────────────────────────────────────────────────────────┘
                          ↓ (if pass)
┌─────────────────────────────────────────────────────────────┐
│ Wave 2: Critical Validators (Parallel, Blocking)            │
│ ┌─────────────────┐  ┌─────────────────┐                   │
│ │ security        │  │ performance     │  → Any Fail       │
│ └─────────────────┘  └─────────────────┘    Blocks         │
└─────────────────────────────────────────────────────────────┘
                          ↓ (if pass)
┌─────────────────────────────────────────────────────────────┐
│ Wave 3: Specialized Validators (Parallel, Pattern-Triggered)│
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
│ │ <v-a>  │ │ <v-b>  │ │ <v-c>  │ │ <v-d>  │ │ <v-e>  │    │
│ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Consensus Rules

**Global Validators:**
- Both global-codex and global-claude must agree
- If they disagree, escalate to human review
- Tie-breaker: More specific feedback wins

**Critical Validators:**
- ANY failure blocks the task
- Must fix ALL critical issues before re-validation
- No partial approvals

**Specialized Validators:**
- Only triggered if relevant files changed
- Failures are advisory unless configured as blocking
- Can proceed with warnings noted

## Bundle-first rule
Before any validator wave, run the guarded bundle helper (`edison qa bundle <root-task>`). Paste the manifest into the QA brief. Validators must load only what the bundle lists.

### Bundle approval marker
- Generate bundle manifest with `edison qa bundle <root-task>`; paste into QA before any validator runs.
- After all blocking validators approve, produce `bundle-approved.json` in the round evidence directory (guards enforce its presence). Promotion `qa wip→done` and `task done→validated` is blocked until `approved=true` in this file.
- QA promotion guards (`edison qa promote` and `edison qa promote <task-id> --status validated`) now enforce both bundle manifest + `bundle-approved.json` existence.

## Sequence (strict order)
1) Automation evidence captured (`command-type-check.txt`, `command-lint.txt`, `command-test.txt`, `command-build.txt`, etc.).
2) Context7 refreshes for all Context7-detected packages; save `context7-<pkg>.txt` markers.
3) Detect changed files → map to validator roster.
4) Update QA with validator list, commands, expected results, evidence links, and bundle manifest.
5) Run validators in waves (respect models and concurrency cap). Summarize each report in QA.
6) Store raw artefacts under `.project/qa/validation-evidence/<task-id>/round-<N>/` and reference them in QA.
7) Move QA/task only after ALL blocking validators approve and the bundle-approved marker exists.

## Failure & Re-runs
- Blocking validator reject → task stays/returns to `wip`; QA → `waiting`; spawn follow-ups in `tasks/todo/`; add "Round N" entry to QA.
- Validator blocked/missing → stop; fix cause; rerun affected validators.
- Each revalidation uses a new `round-<N>` directory; never overwrite prior evidence.

## Round N Rejection Cycle

When validation fails:

```
Round 1: Initial Validation
    ↓ (REJECT)
Task returns to WIP
    ↓
Fix issues identified
    ↓
Round 2: Re-validation
    ↓ (REJECT again?)
Repeat until APPROVE or escalate
```

### Rejection Handling

1. **Read rejection report**: Understand ALL issues
2. **Fix ALL issues**: Don't fix one and re-submit
3. **Re-run failed validators**: Use `edison qa validate --validators=<failed>`
4. **Document fixes**: Update implementation report

### Maximum Rounds

- Configurable via `validation.maxRounds` (default: 3)
- After max rounds, escalate to human review
- Each round's feedback is cumulative

## QA Ownership & Evidence
- Assign a single QA owner; multiple validators may run, but one owner curates the QA brief.
- Name evidence clearly (e.g., `validator-<id>-report.md`, `command-test.txt`, `bundle-approved.json`).
- Validator reports must record the model used and it must match the config.

## Parent vs Child Tasks (Parallel Implementation)

Bundle validation (cluster): Validators MUST review the entire cluster - the parent task + parent QA and all child tasks + their QA - using the bundle manifest from `edison qa bundle`.

- Run the unified validator: `edison qa validate <parent> --session <sid>`.
- It writes a single `bundle-approved.json` under the parent's evidence directory with:
  - `approved` (overall cluster decision)
  - `tasks[]` array with per-task `approved` booleans for every task in the bundle (parent and children).
- QA promotion rules:
  - Parent QA `wip->done` requires the parent-level `bundle-approved.json` with `approved=true`.
  - Child QA `wip->done` is permitted when the parent's `bundle-approved.json` exists and the child's entry shows `approved=true` (no duplicate per-child validation required). If no parent is present, fall back to single-task validation.

Child tasks (owned by implementers) produce their own implementation evidence and can have their QA promoted to `done` when their blocking validators approve. Validators may mark some children approved and others not; the bundle captures per-task approvals. The parent cannot complete until every child in the bundle is approved.

Session completion enforces: parent is `tasks/validated/` with QA in `qa/done|validated`; children are `tasks/validated` (preferred) or `done` if explicitly staged for a follow-up round; child QA is `qa/done|validated` (preferred). Use bundle validation to converge children to validated where possible.

## Validator Follow-ups

### Non-blocking follow-ups - create but do not link
- For non-blocking follow-ups reported by validators, tasks MUST be created in `tasks/todo/` before QA can move `wip -> done`, but MUST NOT be linked as children of the parent (to avoid gating the parent's promotion).
- The guard `edison qa promote` enforces this by calling `edison task ensure_followups --source validator --enforce`.

### When to create follow-up tasks
- Validators may suggest improvements that are not blocking (e.g., "consider adding more edge case tests")
- These suggestions should be captured as follow-up tasks for future sessions
- Non-blocking follow-ups do NOT prevent task approval
- Blocking findings require immediate fixes before approval

## CLI Helpers

### Run Validators (writes reports automatically)

Run the full roster (all waves in order) and write `validator-*-report.md` files into the current round:

```bash
edison qa validate <task-id> --session <session-id> --execute
```

Run a single validator (writes `validator-<id>-report.md` for CLI-executed validators; delegated validators emit `delegation-<id>.md` instructions):

```bash
edison qa run <validator-id> <task-id> --session <session-id> --round <N>
```

## Promotion rules
- QA may move `waiting→todo` only when the task is in `tasks/done/`.
- Tasks/QAs move to `validated` only when bundle-approved is true and all blocking validators approved; otherwise remain in `wip/done` with QA in `waiting/todo`.