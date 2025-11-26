# Session Workflow (Active Session Playbook)


> **Canonical Location**: `.edison/core/guidelines/orchestrators/SESSION_WORKFLOW.md` (bundled with the core guidelines).

Canonical path: .edison/core/guidelines/orchestrators/SESSION_WORKFLOW.md

This guide assumes you already ran the appropriate intake prompt (`START.SESSION.md` or a dedicated shared-QA variant) and a session record exists under `.project/sessions/`. From this point on, every action revolves around the tasks and QA briefs listed in that session file.

## CLI naming (dispatcher + auto-start)
- Use the dispatcher: `edison session start|next|verify|close|recovery --session <id>`.
- **Auto-start:** `edison session start` bootstraps the orchestrator using ConfigManager (core → pack → project YAML overlays), delivers the prompt template to the active agent, and restores/creates the session record. Run this once per session; it replaces legacy `scripts/session` wrappers.
- Prompt templates for the current role/session are injected automatically on start; do not hand-edit the rendered prompt.
- Set the project owner environment variable (`<PROJECT>_OWNER`) if your orchestration layer expects it for default session ownership.

## Worktree isolation (new)
- Sessions operate from an isolated git worktree created under `../${PROJECT}-worktrees/<session-id>/`.
- Manage lifecycle via `edison git worktree-create|worktree-restore|worktree-archive|worktree-cleanup` (or `edison git worktree-*`). Auto-start invokes create/restore when configured.
- Never develop directly in the primary worktree while a session is active; keep changes confined to the session worktree to prevent cross-session conflicts.

## Session States

Sessions transition through three states:
- **active** (located in `.project/sessions/wip/`)
- **closing** (located in `.project/sessions/done/`)
- **validated** (located in `.project/sessions/validated/`)

Directory Naming: The directory names (`wip/`, `done/`) reflect legacy nomenclature but state metadata is canonical. Always use state names (active/closing/validated) in code and configuration.

## Session Isolation (new)

Session state names map to on-disk directories as follows:

- `.project/sessions/wip/` (active)
- `.project/sessions/done/` (closing)
- `.project/sessions/validated/` (validated)

- <!-- RULE: RULE.SESSION.ISOLATION START -->
- Claiming a task into a session physically moves it under `.project/sessions/wip/<session-id>/tasks/<status>/` (session state: active). Paired QA lives under `.project/sessions/wip/<session-id>/qa/<status>/`.
- While the session is active, operate on the session-scoped queues by passing `--session <id>` (or set your project’s session-owner environment variable so CLIs auto-detect).
- Other agents must never touch items under another session’s `sessions/wip/<id>/` (active) tree. Global queues contain only unclaimed work.
- Session completion restores all session-scoped files back to the global queues, preserving final status.
- <!-- RULE: RULE.SESSION.ISOLATION END -->

## Session Timeouts (WP-002)

- Default inactivity timeout is configured in `.edison/core/defaults.yaml` under `session.timeout_hours` (default: 8).
- Stale detection cadence is `session.stale_check_interval_hours` (default: 1) for schedulers.
- When a session exceeds the timeout window (based on the most recent of `lastActive`, `claimedAt`, or `createdAt`):
  - `edison session detect-stale` detects and automatically cleans up expired sessions.
  - Cleanup restores all session-scoped tasks/QA back to the global queues and moves the session JSON from `sessions/wip/` → `sessions/done/`.
  - `meta.expiredAt` is stamped and an Activity Log entry is appended for auditability.
- All claim paths fail-closed: `edison tasks claim` refuses operations into an expired session.
- Clock skew handling: small positive skew (≤ 5 minutes) in timestamps is tolerated; otherwise the detector treats timestamps conservatively and never leaves sessions indefinitely active.

## Quick checklist (fail-closed) - ORCHESTRATOR

- [ ] Session record in `.project/sessions/wip/` (active) is current (Owner, Last Active, task & QA scope, Activity Log).
- [ ] Every claimed task has a matching QA brief (in `qa/waiting|todo|wip|done`).
- [ ] Implementation delegated to sub-agents (OR done yourself for trivial tasks) with TDD and an Implementation Report per round (`.edison/implementation/OUTPUT_FORMAT.md`).
- [ ] Sub-agents/implementers followed their workflow (tracking stamps, TDD, Context7, automation, reports).
- [ ] Validation delegated to independent validators (NEVER self-validate your own implementation).
- [ ] ALL blocking validators launched (global + critical + triggered specialized with `blocksOnFail=true`).
- [ ] Validators run in batched waves up to concurrency cap; verdicts recorded in QA docs.
- [ ] Approval decision based on ALL blocking validators (if ANY reject → task REJECTED).
- [ ] Rejections keep tasks in `tasks/wip/` and QA in `qa/waiting/`. Follow-up tasks created immediately.
- [ ] Session closes only after `edison session verify --phase closing` then `edison session close <session-id>` pass. Parent task must be `validated`. Child tasks can be `done|validated`. Parent QA must be `done|validated`. Child QA should be `done` when approved in the parent bundle (or `waiting|todo` only if intentionally deferred outside the bundle).
- [ ] State transitions follow `.edison/session-workflow.json`; use guards (`edison tasks ready`, `edison validators bundle`) not manual moves.
- [ ] Auto-start ran (`edison session start`) and worktree isolation is active for this session (external worktree path recorded).

## Context Budget (token minimization)

<!-- RULE: RULE.CONTEXT.BUDGET_MINIMIZE START -->
<!-- ANCHOR: context-budget -->
Keep orchestrator context under roughly 50K tokens by default. Prefer concise summaries and diffs over full files, and aggressively trim stale or redundant content from the session.
Use focused snippets around the relevant change (for example, 80–120 lines of code or a single section of a document) instead of entire files whenever possible.
<!-- RULE: RULE.CONTEXT.BUDGET_MINIMIZE END -->

<!-- RULE: RULE.CONTEXT.NO_BIG_FILES START -->
Avoid loading very large files (logs, generated artefacts, bundled assets) into prompts unless absolutely necessary for the current decision. When large inputs are unavoidable, extract only the minimal relevant portion and reference the full artefact by path.
<!-- RULE: RULE.CONTEXT.NO_BIG_FILES END -->

<!-- RULE: RULE.CONTEXT.SNIPPET_ONLY START -->
When sharing code or documentation with sub-agents, send focused snippets around the change (functions, components, or paragraphs) instead of whole files. Combine multiple small snippets when cross-references are required rather than sending the entire project tree.
<!-- RULE: RULE.CONTEXT.SNIPPET_ONLY END -->

## Active Session Board

| Task State | Required QA State | What to do | Scripts & Notes |
|------------|------------------|------------|-----------------|
| `tasks/todo/` (new follow-ups created during the session) | `qa/waiting/` | Decide whether to claim now. If claimed, move task → `wip/`, create QA via `edison qa new`, and add both IDs to the session scope. | `edison tasks status <id> --status wip`<br/>`edison qa new <id> --session <session-id>` |
| `tasks/wip/` | `qa/waiting/` while implementing | Keep task + QA paired in your session scope. Update `Last Active` after every change, run Context7 + TDD cycle, delegate via Zen MCP as needed. | `edison tasks claim <id> --session <session-id>` updates timestamps + session record. |
| `tasks/wip/` (ready for validation) | `qa/todo/` | Move QA to `todo/` when implementation is in `done/`. Do **not** move the task to `done/` until QA is ready. | `edison qa promote --task <task-id> --to todo` |
| `tasks/done/` | `qa/wip/` | Launch validators in parallel waves (up to cap). Capture findings + evidence paths in QA doc. | Run `edison validators bundle <task-id>` to produce the manifest, then `edison qa promote --task <task-id> --to wip` to begin validation. |
| `tasks/wip/` (after rejection) | `qa/waiting/` | Task returns/stays in `wip/` until fixes are validated. QA re-enters `waiting/` with a “Round N” section summarizing findings. | Spawn follow-ups in `tasks/todo/` + `qa/waiting/` immediately; link them in both task + QA documents. |
| `tasks/validated/` | `qa/validated/` or `qa/done/` | Only promote when **all** blocking validators approve and evidence is linked. Then update the session Activity Log and remove the task from the scope list. | `edison session verify --phase closing` transitions the session to closing, then `edison session close <session-id>` moves the session to `sessions/validated/`. |

> 💡 The board is bidirectional: any time a file is in the wrong combination (e.g., task in `done/` but QA still in `waiting/`), fix the mismatch before proceeding.

### Hierarchy & State Machine

- Session files now live in `.project/sessions/<state>/<session>.json` and store every parent/child relationship plus QA linkage. The canonical transitions are defined in `.edison/session-workflow.json`; `edison session status <id>` renders the Markdown view for humans/LLMs.
<!-- RULE: RULE.LINK.SESSION_SCOPE_ONLY START -->
- Use `.edison/scripts/tasks/new --parent <id>` or `.edison/scripts/tasks/link <parent> <child>` to register follow-ups. Linking MUST only occur within the current session scope; `.edison/scripts/tasks/link` MUST refuse links where either side is out of scope unless `--force` is provided (and MUST log a warning in the session Activity Log).
<!-- RULE: RULE.LINK.SESSION_SCOPE_ONLY END -->
- Before promoting a task to `done/`, run `edison tasks ready <task-id>` to enforce automation evidence, QA pairing, and child readiness (all children in `done|validated`).
- Before invoking validators, run `edison validators bundle <root-task>` to emit the cluster manifest (tasks, QA briefs, evidence directories) and paste it into the QA doc. Validators only accept bundles generated from this script.
- Use `scripts/me whoami|tasks|bundle` for self-audits; this CLI surfaces the tasks you own, their blockers, and the bundle manifest without manually reading JSON.

<!-- RULE: RULE.GUARDS.FAIL_CLOSED START -->
> All status moves are fail-closed and MUST go through guarded Python CLIs (`edison tasks status`, `edison qa promote`, `.edison/scripts/qa/round`, `edison session`). Direct file moves or legacy TS movers are forbidden.
<!-- RULE: RULE.GUARDS.FAIL_CLOSED END -->

<!-- RULE: RULE.GUARDS.NO_MANUAL_MOVES START -->
All task/QA moves MUST go through guarded CLIs (`edison tasks status`, `edison qa promote`, `.edison/scripts/qa/round`, `edison session`). Manual `git mv` or filesystem moves are prohibited.
<!-- RULE: RULE.GUARDS.NO_MANUAL_MOVES END -->

<!-- RULE: RULE.QA.PAIR_ON_WIP START -->
Create and pair a QA brief (`qa/waiting/`) as soon as a task enters `tasks/wip/`. Do not defer QA creation to later phases.
<!-- RULE: RULE.QA.PAIR_ON_WIP END -->

<!-- RULE: RULE.STATE.NO_SKIP START -->
State transitions must be adjacent per the state machine; skipping states (e.g., `todo → validated`) is not allowed.
<!-- RULE: RULE.STATE.NO_SKIP END -->

<!-- RULE: RULE.SESSION.CLOSE_NO_BLOCKERS START -->
Close a session only when all scoped tasks are `validated`, paired QA are `done|validated`, and no unresolved blockers or report/schema errors remain.
<!-- RULE: RULE.SESSION.CLOSE_NO_BLOCKERS END -->

## 1. Keep the session record alive
1. Use `edison session status <session-id>` at least every two hours to confirm every scoped task/QA still lives where you expect.
2. Every time you run `edison tasks claim`/`status` or `edison qa new`, pass `--session <session-id>` so the scope lists stay accurate and the session’s `Last Active` is refreshed.
3. Work inside the session worktree shown by `edison session status` (typically `../${PROJECT}-worktrees/<session-id>`). If missing, restore with `edison git worktree-restore <session-id>` (or `worktree-create` for new sessions).
4. Log meaningful milestones (delegation dispatched, validators launched, follow-ups spawned, blockers encountered) in the session file’s Activity Log. This is the source of truth for resuming after crashes.

## 2. Implementation loop (per task) - ORCHESTRATOR DUTIES

**Your role:** Coordinate implementation (delegate OR do yourself), monitor progress, handle results.

### 2.1. Setup and Planning

1. **Confirm QA exists:** `find .project/qa -name "*<task-id>*-qa.md"`. If missing, create via `edison qa new <task-id> --session <session-id>`.

2. **Decide approach:**
   - **Option A: Delegate to sub-agent** (recommended for complex/specialized work)
   - **Option B: Implement yourself** (only for trivial tasks where delegation overhead isn't worth it)

3. **Use session next for guidance:**
   ```bash
   edison session next <session-id>
   ```
   Shows delegation suggestions, validator roster, related tasks, rules.

### 2.2a. If Delegating (RECOMMENDED)

**Delegate according to `.edison/delegation/config.json`:**

1. **Launch sub-agent via your project's orchestration layer:**
   ```bash
   # Example: Delegating implementation to a specialized agent role
   <orchestrator-cli> --role <agent-name> --task <task-id> --prompt-source .edison/implementation/IMPLEMENTER_WORKFLOW.md
   ```

2. **Sub-agent will handle:**
   - ✅ Calling `scripts/track start` (their mandatory first step)
   - ✅ Following TDD (RED → GREEN → REFACTOR)
   - ✅ Querying Context7 for post-training packages
   - ✅ Filling implementation report as they work
   - ✅ Running automation commands (type-check, lint, test, build)
   - ✅ Calling `scripts/track complete` (their mandatory last step)

3. **Monitor progress:**
   ```bash
   scripts/track active  # See if sub-agent is still working
   scripts/track stale   # Detect if sub-agent crashed
   ```

4. **When sub-agent reports back:**
   - Review their implementation report at `.project/qa/validation-evidence/<task-id>/round-1/implementation-report.json`
   - Check for blockers, follow-ups, completion status
   - Store `continuation_id` in task file and session record

### 2.2b. If Implementing Yourself (RARE)

**⚠️ WARNING:** Only do this for TRIVIAL tasks. For anything non-trivial, delegate!

**If you must implement yourself:**

1. **YOU must follow `.edison/implementation/IMPLEMENTER_WORKFLOW.md`:**
   - Call `scripts/track start --task <id> --type implementation --model claude`
   - Follow TDD, query Context7, fill report, run automation
   - Call `scripts/track complete`

2. **This is the SAME process sub-agents follow** - you get no shortcuts!

### 2.3. Handle Implementation Results

1. **Review implementation report** for blockers and follow-ups.

2. **Spawn follow-up tasks** (if any discovered):
   - Create in `tasks/todo/` with paired QA in `qa/waiting/`
   - Link to parent via `.edison/scripts/tasks/link`
   - Decide if they belong in current session (claim now) or future session (leave in todo/)

3. **Update session Activity Log** with implementation milestone.

4. **When ALL related work is done** (task + all follow-ups):
   - Run `edison validators bundle <root-task-id>` to generate validation manifest
   - Paste manifest into root task's QA brief
   - Move QA from `waiting/` → `todo/` to signal ready for validation

### 2.4. Verification Before Validation

**Run readiness check:**
```bash
edison tasks ready <task-id> --session <session-id> [--run] [--disable-tdd --reason \"justification\"]
```

This guard verifies:
- ✅ Implementation report exists with tracking stamps (startedAt, completedAt, processId)
- ✅ Automation evidence files present (command-type-check.txt, command-lint.txt, command-test.txt, command-build.txt)
- ✅ QA brief paired
- ✅ Child tasks ready (if any)
- ✅ Context7 auto-detected packages from the git diff have matching `context7-<pkg>.txt` markers (HMAC stamped when enabled)
- ✅ Evidence set matches config-driven requirements from ConfigManager (core → pack → project overlays)

<!-- RULE: RULE.PARALLEL.PROMOTE_PARENT_AFTER_CHILDREN START -->
Parent tasks MUST NOT move to `done/` until every child task in the session scope is `done|validated`.
<!-- RULE: RULE.PARALLEL.PROMOTE_PARENT_AFTER_CHILDREN END -->

**If guard fails:** Fix issues before proceeding. Guard errors are explicit about what's missing.

> **💡 CRITICAL WORKFLOW AID:** After every action (claim, delegate, status change), run `edison session next <session-id>` to see the next steps and stay "on rails." This enhanced orchestration helper:
> - Shows ALL applicable rules BEFORE actions (proactive, not just at enforcement)
> - Displays complete validator roster with model bindings (prevents forgetting validators or using wrong models)
> - Shows delegation suggestions with detailed reasoning from `.edison/delegation/config.json`
> - Lists related tasks (parent/child/sibling) for context
> - Provides decision points (concurrency cap, wave batching, optional validators)
> - Returns precise commands with rule references so you never miss a step
>
> Use `--json` for programmatic parsing or default human-readable format for manual review. The planner reads the session JSON + state machine and returns information-rich suggestions while leaving final decisions to you based on code review context.

## 3. Validator orchestration - ORCHESTRATOR DUTIES

**Your role:** Launch independent validators, monitor progress, aggregate verdicts, make approval decision.

### 3.1. Validator Independence Rules

<!-- RULE: RULE.VALIDATION.INDEPENDENCE START -->
**🔴 CRITICAL:** Validators MUST be independent from implementation.

**FORBIDDEN:**
- ❌ Orchestrator validating their own implementation
- ❌ Same model validating its own work (e.g., Codex validating Codex's implementation)
- ❌ Skipping validators to save time
- ❌ Treating optional validators as "good enough"

**REQUIRED:**
- ✅ Launch ALL blocking validators (global + critical + triggered specialized with `blocksOnFail=true`)
- ✅ Use DIFFERENT models for validation than implementation (if possible)
- ✅ Launch validators via delegation (Zen MCP) so they run independently
- ✅ Wait for ALL blocking validators to complete before making approval decision

**Rationale:** Independent validation catches blind spots. Self-validation is confirmation bias.
<!-- RULE: RULE.VALIDATION.INDEPENDENCE END -->

### 3.2. Prepare for Validation

1. **Verify task is ready:**
   - Task in `tasks/done/`
   - QA in `qa/todo/`
   - Implementation report complete with tracking stamps
   - Automation evidence files present

2. **Move QA to wip:**
   ```bash
   edison qa promote --task <task-id> --to wip
   ```
   This signals validation has started.

3. **Identify required validators:**
   ```bash
   edison session next <session-id>
   ```
   Shows complete validator roster (always-required + triggered + optional).

### 3.3. Launch Validators (DELEGATED)

**Launch validators in parallel waves up to concurrency cap (default 5):**

#### Wave 1: Global Validators (MANDATORY, BLOCKING)

```bash
# Global Validator (Model 1)
<validator-cli> --model <model-1> --role validator-<model-1>-global --task <task-id> --qa .project/qa/wip/<task-id>-qa.md

# Global Validator (Model 2)
<validator-cli> --model <model-2> --role validator-<model-2>-global --task <task-id> --qa .project/qa/wip/<task-id>-qa.md
```

#### Wave 2: Critical Validators (MANDATORY, BLOCKING)

```bash
# Security
<validator-cli> --model <model> --role validator-security --task <task-id> --qa .project/qa/wip/<task-id>-qa.md

# Performance
<validator-cli> --model <model> --role validator-performance --task <task-id> --qa .project/qa/wip/<task-id>-qa.md
```

#### Wave 3: Specialized Validators (TRIGGERED, BLOCKING IF `blocksOnFail=true`)

**Only launch if file patterns match** (session next shows which are triggered):

```bash
# Specialized Validators (triggered by configured file patterns)
<validator-cli> --model <model> --role validator-<type> --task <task-id> --qa .project/qa/wip/<task-id>-qa.md

# Check orchestrator manifest for active pack validators and their trigger patterns
```

### Validator Wave Details

#### Wave 1: Global Validators
##### Codex Global
- Model: codex
- Scope: All changes
- Blocking: YES
- Focus: Code quality, TDD compliance, security basics

##### Claude Global
- Model: claude
- Scope: All changes
- Blocking: YES
- Focus: Architecture, patterns, best practices

##### Gemini Global
- Model: gemini
- Scope: All changes
- Blocking: NO (advisory)
- Focus: Alternative perspectives, edge cases

#### Wave 2: Critical Validators
##### Security
- Model: codex
- Scope: All changes
- Blocking: YES
- Focus: OWASP Top 10, auth, input validation, secrets exposure

##### Performance
- Model: codex
- Scope: All changes
- Blocking: YES
- Focus: Bundle size, query efficiency, caching, N+1 detection

#### Wave 3: Specialized Validators

**Validators from Active Packs** (check orchestrator manifest for current roster):

##### API Validator
- Triggers: API file patterns from pack configuration
- Focus: REST/API patterns, error handling, response format, schema validation

##### Testing Validator
- Triggers: Test file patterns from pack configuration
- Focus: TDD compliance, coverage, test quality, no mocks on critical paths

##### Database Validator
- Triggers: Database file patterns from pack configuration
- Focus: Schema design, migrations, query safety, relationships

##### UI Component Validator
- Triggers: Component file patterns from pack configuration
- Focus: Component patterns, best practices, accessibility

##### Frontend Framework Validator
- Triggers: Framework file patterns from pack configuration
- Focus: Framework patterns, routing, data loading, caching

**Note**: Specific models, blocking status, and trigger patterns are defined in `{{PROJECT_EDISON_DIR}}/_generated/orchestrator-manifest.json` based on active packs.

**Each validator will handle:**
- ✅ Calling `scripts/track start` (their mandatory first step)
- ✅ Loading context (QA brief, implementation report, evidence, git diff)
- ✅ Querying Context7 (if context7Required in their config)
- ✅ Filling validator report as they validate
- ✅ Determining verdict (approve/reject/blocked)
- ✅ Calling `scripts/track complete` (their mandatory last step)

### 3.4. Monitor Validators

```bash
# See which validators are running
scripts/track active

# Detect crashed validators
scripts/track stale
```

**If validator crashes:** Remove stale report, investigate logs, re-launch validator.

### 3.5. Aggregate Verdicts

**When all validators report back:**

1. **Read each validator report:**
   - `.project/qa/validation-evidence/<task-id>/round-1/validator-<id>-report.json`

2. **Check verdicts:**
   - ✅ `approve` - Validator passed the task
   - ❌ `reject` - Validator found blocking issues
   - ⚠️ `blocked` - Validator couldn't complete (missing evidence, etc.)

3. **Aggregate blocking validators:**
   - ALL blocking validators (global + critical + specialized with `blocksOnFail=true`) MUST approve
   - If ANY blocking validator rejects, task is REJECTED
   - If ANY blocking validator is blocked, task is BLOCKED (fix and re-run)

### 3.6. Make Approval Decision

#### If ALL Blocking Validators Approve:

1. **Move task:** `tasks/done/` → `tasks/validated/`
2. **Move QA:** `qa/wip/` → `qa/done/`
3. **Update session Activity Log** with validation milestone
4. **Update QA brief** with final "Validator Findings & Verdicts" section summarizing all reports

#### If ANY Blocking Validator Rejects:

1. **Keep task in:** `tasks/wip/` (or return from `done/` to `wip/`)
2. **Move QA:** `qa/wip/` → `qa/waiting/`
3. **Add "Round N" section to QA brief** with:
   - Date/time
   - Status: REJECTED
   - Validator findings (blocking issues)
   - Follow-up task IDs
4. **Spawn follow-up tasks:**
   - Create in `tasks/todo/` with paired QA in `qa/waiting/`
   - Link to parent
   - Decide if current session or future session
5. **Update session Activity Log** with rejection and follow-ups

**After fixes:** Repeat validation (Round 2).

### 3.7. Summarize in QA Brief

**Update QA brief with validator verdicts:**

```markdown
## Validator Findings & Verdicts

### Global Validator 1 ✅ APPROVED
- Report: `.project/qa/validation-evidence/<task-id>/round-1/validator-<name>-report.json`
- Verdict: Approve
- Summary: Excellent implementation quality...

### Global Validator 2 ✅ APPROVED
- Report: `.project/qa/validation-evidence/<task-id>/round-1/validator-<name>-report.json`
- Verdict: Approve
- Summary: Strong TDD compliance...

### Security ❌ REJECTED
- Report: `.project/qa/validation-evidence/<task-id>/round-1/validator-security-report.json`
- Verdict: Reject
- Summary: Critical issue found - missing rate limiting...
- Blocking Issues: 2 (1 critical, 1 high)
- Follow-Ups: Task <id> created for rate limiting

### Performance ✅ APPROVED
- Report: `.project/qa/validation-evidence/<task-id>/round-1/validator-performance-report.json`
- Verdict: Approve
- Summary: No performance concerns...

## Final Decision: REJECTED
- Reason: Security validator found blocking issues
- Action: Task <id> created and claimed for fixes
- Next Step: After <id> completes, resubmit for Round 2 validation
```

> **💡 MONITORING UTILITIES:**
> - `scripts/track active` - See all running validators (PIDs, models, start times)
> - `scripts/track stale` - Detect crashed validators (PID no longer running)
> - `scripts/track heartbeat` - Not typically needed (validators should complete quickly)

## 4. Handling rejections & follow-ups
1. Rejected tasks **stay** in `.project/tasks/wip/`. Never move them back to `todo/`—they are still active work.
2. Move the QA file to `qa/waiting/` and add a “Round N” section capturing:
   - Date/time
   - Status (`REJECTED`)
   - Validator findings
   - Follow-up task IDs
3. Create follow-up tasks with numbering gaps (≥50). Each follow-up gets:
   - Task file in `tasks/todo/`
   - QA brief in `qa/waiting/`
   - References back to the originating QA and session file
4. Decide whether the follow-up belongs in the current session:
   - If yes, claim it immediately (intake-style) and add it to the session scope.
   - If no, leave it in `tasks/todo/` for a future session but document the handoff.
5. After fixes are implemented, move the parent task to `done/`, QA to `todo/`, and re-run the validator waves (Round 2, Round 3, etc.).

<!-- RULE: RULE.FOLLOWUPS.LINK_ONLY_BLOCKING START -->
### Linking semantics for follow-ups (fail-closed)
- Linking a follow-up as a child of the parent denotes a hard dependency. If a follow-up is linked, it MUST be claimed into the same session and will block promotion of the parent until the child is `done` or `validated`.
- Only follow-ups marked as blocking (e.g., `blockingBeforeValidation=true` in the implementation report) should be linked to the parent.
- The readiness gate runs `.edison/scripts/tasks/ensure-followups --source implementation --enforce` and then enforces `childIds` readiness before `wip → done`.
<!-- RULE: RULE.FOLLOWUPS.LINK_ONLY_BLOCKING END -->

<!-- RULE: RULE.FOLLOWUPS.DEDUPE_FIRST START -->
### Duplicate prevention before creation
- Before creating any follow-up, search existing tasks by slug/title similarity. If a near-duplicate (≥0.82) exists, do NOT create a new task—link/record the existing ID where appropriate.
- The helper `.edison/scripts/tasks/ensure-followups` performs this check automatically.
<!-- RULE: RULE.FOLLOWUPS.DEDUPE_FIRST END -->

### Parent Requeue (auto‑suggested)
- When a parent task is set to `blocked` and all its child follow‑ups are `done` or `validated`, the Active Session “next” plan will suggest:
  - `task.unblock.wip` → `edison tasks status <parent> --status wip`
  - If automation evidence is present for the parent (type/lint/test/build + implementation‑report), it will also suggest:
    - `task.promote.done` → `edison tasks status <parent> --status done`
    - Followed by the usual QA `waiting → todo` then validator waves.
- Rationale: this keeps the parent on rails without manual bookkeeping once dependent work finishes.

## 5. Session close-out
1. When every scoped task + QA is in `validated/`, update the session Activity Log with a completion note.
2. Run `edison session complete <session-id>`:
   - Confirms every listed task lives in `tasks/validated/`.
   - Confirms every listed QA lives in `qa/validated/` (or `qa/done/` if your policy treats it as final).
   - Verifies each task has a populated evidence directory.
3. If the script reports discrepancies, resolve them immediately (do not archive the session until it passes).
4. On success, the script moves the session file from `sessions/done/` (closing) → `sessions/validated/`. Push commits only after this promotion, ensuring all documentation aligns.

## 6. Crash recovery / continuation
- Session interruped? Run `edison session status <session-id>` to regenerate the scope snapshot, reopen each listed task/QA, and continue from the recorded Activity Log.
- Rejoining later? Claim/resume each task via `edison tasks claim --session <session-id>` so `Last Active` timestamps confirm the work is in progress.
- Handing off? Mention the session ID inside each task/QA file’s metadata so the next orchestrator can pick it up.

---

**References**
- `.edison/AGENTS.md` – orchestration policies & delegation guardrails
- `.edison/guidelines/VALIDATION.md` – validator gate specifics
- `.edison/guidelines/TDD.md` – RED/GREEN/REFACTOR protocol
- `.edison/guidelines/HONEST_STATUS.md` – directory semantics + reporting rules
- `.edison/delegation/config.json` – sub-agent decision tables
- `.edison/validators/config.json` – validator triggers + block/allow list
