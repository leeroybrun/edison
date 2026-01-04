# Validation (Core)


Run after implementation is complete and before a task can advance beyond `{{fn:semantic_state("task","done")}}/`. QA briefs are the canonical validation record.

## Validation Checklist (fail-closed)
- Build the triggered validator roster from the merged `validation.validators` config (core → packs → user → project) and the task/session file context (git diff + primary files).
- Automation evidence passing for the round (config-driven; see required evidence for the task’s validation preset).
- QA brief exists in `qa/{{fn:semantic_states("qa","waiting,todo,wip","brace")}}` with roster, commands, expected results, and evidence links; never duplicate QA files.
- Bundle manifest generated before launching validators (see Bundle section).
- Context7 refreshed for every Context7-detected package; add `context7-<pkg>.txt` markers per package in the round evidence directory.
- Required validators launched in waves up to the concurrency cap; record the model used.
- If any blocking validator rejects → task stays in `{{fn:semantic_state("task","wip")}}`, QA returns to `{{fn:semantic_state("qa","waiting")}}`, follow-ups created.
- If any validator is blocked or missing, halt and resolve before proceeding.

## Validator Roster & Waves
To inspect the computed roster for a task (including triggered validators and wave membership), run:

```bash
edison qa validate <task-id> --session <session-id> --dry-run
```

**Global (blocking):** all global validators in the roster always run first and must approve.
**Critical (blocking):** every critical validator in the roster is blocking for promotion.
**Comprehensive (triggered, specialized):** driven by file triggers in the active validator roster (run `edison read AVAILABLE_VALIDATORS`); the active set is listed in `AVAILABLE_VALIDATORS.md`.
**Comprehensive (triggered, specialized, blocking if `blocking=true`):** driven by validator `triggers` patterns in merged config and the task/session file context.

Wave order (mandatory): Global → Critical → Comprehensive (triggered). Launch in parallel per wave up to the configured cap; batch overflow.

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
│ Wave 3: Comprehensive Validators (Parallel, Pattern-Triggered)│
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

**Comprehensive Validators:**
- Only triggered if relevant files changed
- Failures are advisory unless configured as blocking
- Can proceed with warnings noted

## Bundle-first rule
Before any validator wave, run the guarded bundle helper (`edison qa bundle <task> --scope auto`). Paste the manifest into the QA brief. Validators must load only what the bundle lists.

### Bundle approval marker
- Generate bundle manifest with `edison qa bundle <task> --scope auto`; paste into QA before any validator runs.
- After all blocking validators approve, produce `{{config.validation.artifactPaths.bundleSummaryFile}}` in the round evidence directory (guards enforce its presence). Promotion `qa {{fn:semantic_state("qa","wip")}}→{{fn:semantic_state("qa","done")}}` and `task {{fn:semantic_state("task","done")}}→{{fn:semantic_state("task","validated")}}` is blocked until `approved=true` in this file.
- QA promotion guards (`edison qa promote` and `edison qa promote <task-id> --status validated`) now enforce both bundle manifest + `{{config.validation.artifactPaths.bundleSummaryFile}}` existence.

## Sequence (strict order)
1) Automation evidence captured (required: {{fn:required_evidence_files("inline")}}).
2) Context7 refreshes for all Context7-detected packages; save `context7-<pkg>.txt` markers.
3) Detect changed files → map to validator roster.
4) Update QA with validator list, commands, expected results, evidence links, and bundle manifest.
5) Run validators in waves (respect models and concurrency cap). Summarize each report in QA.
6) Store raw artefacts under `{{fn:evidence_root}}/<task-id>/round-<N>/` and reference them in QA.
7) Move QA/task only after ALL blocking validators approve and `approved=true` is recorded in `{{config.validation.artifactPaths.bundleSummaryFile}}`.

## Failure & Re-runs
- Blocking validator reject → task stays/returns to `{{fn:semantic_state("task","wip")}}`; QA → `{{fn:semantic_state("qa","waiting")}}`; spawn follow-ups in `{{fn:tasks_root}}/{{fn:semantic_state("task","todo")}}/`; add "Round N" entry to QA.
- Validator blocked/missing → stop; fix cause; rerun affected validators.
- Each revalidation uses a new `round-<N>` directory; never overwrite prior evidence.

## Round N Rejection Cycle

When validation fails:

```
Round 1: Initial Validation
    ↓ (REJECT)
Task returns to {{fn:semantic_state("task","wip")}}
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

- Configurable via `validation.maxRounds` (default: {{config.validation.maxRounds}})
- After max rounds, escalate to human review
- Each round's feedback is cumulative

## QA Ownership & Evidence
- Assign a single QA owner; multiple validators may run, but one owner curates the QA brief.
- Name evidence clearly (e.g., `validator-<id>-report.md`, {{fn:required_evidence_files("inline")}}, `{{config.validation.artifactPaths.bundleSummaryFile}}`).
- Validator reports must record the model used and it must match the config.
- Evidence must be reviewed, not just generated: if a captured command fails, fix and re-run until `exitCode: 0`. Before session close, satisfy any configured `validation.sessionClose.*` evidence requirements.

## Hierarchy vs Validation Bundles

Edison supports two distinct ways to define a validation “cluster”:
- **Hierarchy (`--scope hierarchy`)**: the root task plus all descendants via parent/child links (decomposition/follow-up structure).
- **Validation bundle (`--scope bundle`)**: the root task plus all tasks with `bundle_root == <root>` (validation grouping, independent of hierarchy).
- **Auto (`--scope auto`)**: prefers `bundle` when bundle members exist; otherwise falls back to `hierarchy` when descendants exist; otherwise validates a single task.

Bundle validation (cluster): Validators MUST review the entire cluster using the bundle manifest from `edison qa bundle ... --scope <scope>`.

- Run: `edison qa validate <task> --scope <auto|hierarchy|bundle> --session <sid> --execute`
- Evidence anchor: validators execute once at the **resolved root task**, and write `{{config.validation.artifactPaths.bundleSummaryFile}}` under the root’s round evidence directory.
- For bundle members: Edison mirrors the bundle summary into each member’s evidence round directory so per-task promotion checks remain deterministic and task-local.

Task-level evidence remains per task (implementation reports, command evidence, Context7 markers). Bundle validation is about *validator execution + approval aggregation*, not about collapsing implementation evidence.

Session completion enforces: parent is `{{fn:task_state_dir("validated")}}/` with QA in `{{fn:semantic_states("qa","done,validated","pipe")}}`; children are `{{fn:semantic_state("task","validated")}}` (preferred) or `{{fn:semantic_state("task","done")}}` if explicitly staged for a follow-up round; child QA is `{{fn:semantic_states("qa","done,validated","pipe")}}` (preferred). Use bundle validation to converge children to validated where possible.

## Validator Follow-ups

### Non-blocking follow-ups - create but do not link
- For non-blocking follow-ups reported by validators, tasks MUST be created in `{{fn:task_state_dir("todo")}}/` before QA can move `{{fn:semantic_state("qa","wip")}} -> {{fn:semantic_state("qa","done")}}`, but MUST NOT be linked as children of the parent (to avoid gating the parent's promotion).
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
- QA may move `{{fn:semantic_state("qa","waiting")}}→{{fn:semantic_state("qa","todo")}}` only when the task is in `{{fn:task_state_dir("done")}}/`.
- Tasks/QAs move to `{{fn:semantic_state("task","validated")}}` / `{{fn:semantic_state("qa","validated")}}` only when all blocking validators approved and `{{config.validation.artifactPaths.bundleSummaryFile}}` records `approved=true`; otherwise remain in `{{fn:semantic_states("task","wip,done","pipe")}}` with QA in `{{fn:semantic_states("qa","waiting,todo","pipe")}}`.
