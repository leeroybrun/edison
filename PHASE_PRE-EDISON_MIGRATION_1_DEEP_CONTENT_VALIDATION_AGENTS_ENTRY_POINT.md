# DEEP CONTENT VALIDATION: AGENTS.md Entry Point
## Pre-Edison vs Post-Edison Comparison

**Date**: 2025-11-25
**Validator**: Claude Code Agent
**Status**: CRITICAL GAPS IDENTIFIED

---

## EXECUTIVE SUMMARY

The post-Edison architecture has **undergone significant restructuring** that introduces **5 CRITICAL GAPS** in the entry point documentation:

1. **Missing Intake Checklists** (START.SESSION.md, START.AUDIT.md)
2. **Displaced Mandatory Preload List** (manifest.json structure changed)
3. **Broken Directive Navigation** (guidelines moved to .edison/core)
4. **Missing Quick-Start CLI Commands** (session next, scripts/rules, etc.)
5. **Lost Orchestration Scripts Guidance** (session, rules, qa, tasks scripts)

**Severity**: HIGH - Agents will fail to orient themselves without comprehensive entry point documentation.

---

## SECTION-BY-SECTION COMPARISON

### PRE-EDISON ENTRY POINT: /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/AGENTS.md

**Total Content**: 110 lines (21 distinct sections)
**Entry Point Strategy**: Single, self-contained orchestration guide
**Navigation Model**: AGENTS.md → manifest.json → guidelines → agent briefs

#### All Sections in Pre-Edison AGENTS.md:

| # | Section | Line Range | Purpose |
|---|---------|-----------|---------|
| 1 | Header + Deployment Note | 1-5 | Context setting |
| 2 | Agent Compliance Checklist (Fail-Closed) | 7-20 | 13 critical guardrails |
| 3 | Mandatory Preload | 24-39 | Explicit file list + CLI usage |
| 4 | Proactive vs Reactive (what to run when) | 40-44 | 4 CLI patterns for different scenarios |
| 5 | Quick Navigation | 47-54 | Directory structure guide |
| 6 | Context Budget Rules (3 inline rules) | 56-66 | RULE.CONTEXT.* blockers |
| 7 | Rule Registry | 68-71 | How to use scripts/rules |
| 8 | Session Workflow | 73-75 | Points to guidelines + START.SESSION.md |
| 9 | Task, QA, Session Directories | 77-80 | Directory structure + tools |
| 10 | Orchestration Model Summary | 82-84 | Sub-agent delegation rules |
| 11 | References | 86-92 | Anchor links to all critical files |
| 12 | Session Isolation | 96-100 | File movement + CLI usage |
| 13 | Parallel Implementation Pattern | 102-109 | Multi-implementer workflow |

#### Pre-Edison AGENTS.md also references:

- **START.SESSION.md** (35 lines) - Session intake checklist
- **START.AUDIT.md** (27 lines) - QA/reclaim intake checklist
- **manifest.json** - Authoritative preload list + orchestration config
- **Mandatory guidelines**: 8 files (SESSION_WORKFLOW, HONEST_STATUS, VALIDATION, QUALITY, TDD, CONTEXT7, GIT_WORKFLOW, EPHEMERAL_SUMMARIES_POLICY, DELEGATION)
- **Config files**: delegation/config.json, validators/config.json, rules/registry.json

**Design Philosophy**: Fail-closed compliance checklist + guided navigation to mandatory files.

---

### POST-EDISON ENTRY POINT: /Users/leeroy/Documents/Development/wilson-leadgen/.agents/README.md

**Total Content**: 295 lines (20 distinct sections)
**Entry Point Strategy**: Configuration overview + context management guide
**Navigation Model**: README.md → AGENTS.md → guidelines (now split: .agents/ + .edison/core/) → agents

#### All Sections in Post-Edison README.md:

| # | Section | Line Range | Purpose |
|---|---------|-----------|---------|
| 1 | Purpose + Status | 1-7 | High-level overview |
| 2 | Quick Start (3 items) | 10-17 | References AGENTS.md + guides |
| 3 | Configuration Authority | 18-20 | Points to .edison/core/ (NEW) |
| 4 | Multi-Validator Architecture | 24-38 | Validator system overview (NEW) |
| 5 | FILES IN THIS DIRECTORY | 42-59 | Directory guide |
| 6 | agents/ Subdirectory | 62-107 | 6 agent profiles (detailed) |
| 7 | AGENTS_SUMMARY.md | 111-123 | Reference to separate file |
| 8 | Packs & Overlays | 127-135 | Pack system guidance (NEW) |
| 9 | HOW THE ORCHESTRATOR SHOULD USE | 139-181 | Session start protocol + execution patterns |
| 10 | INTEGRATION WITH PROJECT | 184-201 | .agents/ vs .project/ distinction |
| 11 | KEY ORCHESTRATION PRINCIPLES | 204-233 | 5 core principles |
| 12 | ORCHESTRATION PATTERNS | 237-268 | 3 parallel/sequential patterns |
| 13 | SUCCESS METRICS | 272-288 | Quality targets |

#### Post-Edison README.md references:

- **.AGENTS.md** (not found in working directory; referenced but unclear if it exists)
- **TDD_GUIDE.md**, **VALIDATION_GUIDE.md** (mentioned but not anchored in mandatory preload)
- **.edison/core/validators/config.json** (moved outside .agents/)
- **.edison/core/delegation/config.schema.json** (moved outside .agents/)
- **agents/ subdirectory** (detailed coverage)
- **guidelines/** (referenced but no comprehensive mandatory list)
- **.edison/packs/** (new pack system references)

**Design Philosophy**: Configuration overview + best practices guide; assumes knowledge of .agents/AGENTS.md.

---

## CRITICAL GAPS ANALYSIS

### GAP #1: Missing Intake Checklists (SEVERITY: CRITICAL)

**Pre-Edison**: Two dedicated intake prompts:
- **START.SESSION.md** (35 lines) - Initial session intake for fresh implementation
- **START.AUDIT.md** (27 lines) - Shared QA + reclaim intake

Both files contain:
- Checklist structure for new agents
- Explicit CLI commands to run
- QA bundle rules + validation workflow
- Follow-up task creation guidance

**Post-Edison**:
- ✗ START.SESSION.md NOT FOUND
- ✗ START.AUDIT.md NOT FOUND
- ⚠ README.md contains vague "SESSION START PROTOCOL" (lines 141-165) but lacks:
  - Explicit checklist format
  - CLI command examples (missing `scripts/session new`, `scripts/tasks/claim`)
  - QA bundle rules
  - Reclaim task guidance

**Impact**: New agents cannot self-orient. They must infer the intake process from scattered documentation instead of following a single checklist.

**Required Recovery**:
```
Create or restore:
1. .agents/START.SESSION.md (35 lines) - Fresh implementation intake
2. .agents/START.AUDIT.md (27 lines) - QA/reclaim audit intake
```

---

### GAP #2: Missing/Displaced Mandatory Preload List (SEVERITY: CRITICAL)

**Pre-Edison manifest.json defines**:
```json
"mandatory": [
  ".agents/AGENTS.md",
  ".agents/session-workflow.json",
  ".agents/guidelines/SESSION_WORKFLOW.md",
  ".agents/implementation/IMPLEMENTER_WORKFLOW.md",
  ".agents/validators/VALIDATOR_WORKFLOW.md",
  ".agents/guidelines/HONEST_STATUS.md",
  ".agents/guidelines/VALIDATION.md",
  ".agents/guidelines/QUALITY.md",
  ".agents/guidelines/TDD.md",
  ".agents/guidelines/CONTEXT7.md",
  ".agents/guidelines/GIT_WORKFLOW.md",
  ".agents/guidelines/EPHEMERAL_SUMMARIES_POLICY.md",
  ".agents/guidelines/DELEGATION.md",
  ".agents/implementation/OUTPUT_FORMAT.md",
  ".agents/rules/registry.json",
  ".agents/validators/config.json",
  ".agents/delegation/config.json",
  ".cursor/rules/00-canonical-agents.mdc",
  ".cursor/rules/01-validation-guard.mdc"
]
```

**Pre-Edison also has**:
- `manifest.json` (142 lines) - Centralized orchestration config
- `session-workflow.json` - Session state machine reference

**Post-Edison**:
- ✗ No top-level manifest.json file (moved to .edison/core/)
- ✗ No preload list in README.md
- ✗ Mandatory files scattered across:
  - `.agents/config/` (delegation.yml, validators.yml, project.yml, etc.)
  - `.agents/guidelines/` (only Wilson-specific overlays, not core guides)
  - `.edison/core/guidelines/` (core framework guides, not curated)
- ⚠ README.md says "Mandatory Preloads (Session Start)" (lines 10-12) but only lists:
  - TDD_GUIDE.md
  - VALIDATION_GUIDE.md
  - (missing 15+ other mandatory files)

**Impact**: Agents don't know what MUST be preloaded before work starts. They may skip critical files like DELEGATION, CONTEXT7, VALIDATION.

**Required Recovery**:
```
Create .agents/manifest.json with complete mandatory list:
1. Framework core (SESSION_WORKFLOW, DELEGATION, TDD, CONTEXT7, VALIDATION, QUALITY, GIT_WORKFLOW, EPHEMERAL_SUMMARIES_POLICY, HONEST_STATUS)
2. Implementation guides (IMPLEMENTER_WORKFLOW, OUTPUT_FORMAT)
3. Validator guides (VALIDATOR_WORKFLOW)
4. Config files (validators.yml, delegation.yml, config.schema.json)
5. Cursor rules (00-canonical-agents.mdc, 01-validation-guard.mdc)
```

---

### GAP #3: Broken Navigation to Guidelines (SEVERITY: HIGH)

**Pre-Edison structure**:
```
.agents/guidelines/
├── SESSION_WORKFLOW.md      ← Active session playbook
├── HONEST_STATUS.md         ← Directory semantics
├── VALIDATION.md            ← QA/validator workflow
├── QUALITY.md               ← Production standards
├── TDD.md                   ← RED → GREEN → REFACTOR
├── CONTEXT7.md              ← Package API reference rules
├── GIT_WORKFLOW.md          ← Commit + branch conventions
├── EPHEMERAL_SUMMARIES_POLICY.md ← Status summary rules
└── DELEGATION.md            ← Model selection rules
```

Pre-Edison AGENTS.md explicitly states:
> "Load EXACTLY the files listed under `mandatory` in `.agents/manifest.json`"

**Post-Edison structure**:
```
.agents/guidelines/
├── overlays/
│   └── wilson-coding-standards.md    ← Project-specific only
├── wilson-architecture.md            ← Project-specific only
├── wilson-auth.md                    ← Project-specific only
├── wilson-database.md                ← Project-specific only
├── wilson-design-system.md           ← Project-specific only
├── wilson-integrations.md            ← Project-specific only
├── wilson-testing.md                 ← Project-specific only
└── wilson-api-conventions.md         ← Project-specific only

.edison/core/guidelines/
├── agents/
│   ├── AGENT_GUIDELINES.md
│   ├── AGENT_WORKFLOW.md
│   ├── CONTEXT7_REQUIREMENT.md
│   ├── TDD_REQUIREMENT.md
│   └── ... (10 agent guidelines)
├── shared/
│   ├── CONTEXT7.md
│   ├── DELEGATION.md
│   ├── EPHEMERAL_SUMMARIES_POLICY.md
│   ├── GIT_WORKFLOW.md
│   ├── HONEST_STATUS.md
│   ├── QUALITY.md
│   ├── TDD.md
│   ├── VALIDATION.md
│   └── ... (8 shared guidelines)
└── orchestrators/
    ├── ORCHESTRATOR_GUIDELINES.md
    ├── SESSION_WORKFLOW.md
    └── ... (4 orchestrator guidelines)
```

**Impact**:
- Agents must know to look in .edison/core/guidelines/ (not discoverable from README.md)
- Core guidelines are "discovered" dynamically, not explicitly listed in mandatory preload
- README.md does NOT guide agents to SESSION_WORKFLOW, DELEGATION, CONTEXT7, etc.
- Missing explicit links to the 19 Edison core guidelines

**Required Recovery**:
```
Update README.md "Mandatory Preloads" section (lines 10-12) to explicitly list:
1. .edison/core/guidelines/orchestrators/SESSION_WORKFLOW.md
2. .edison/core/guidelines/shared/DELEGATION.md
3. .edison/core/guidelines/shared/CONTEXT7.md
4. .edison/core/guidelines/shared/VALIDATION.md
5. ... (all 19 Edison core guidelines)
6. .agents/guidelines/overlays/wilson-coding-standards.md
7. .agents/guidelines/wilson-*.md (all project overlays)
```

---

### GAP #4: Missing Quick-Start CLI Guidance (SEVERITY: HIGH)

**Pre-Edison AGENTS.md (lines 40-44)**:
```markdown
Proactive vs Reactive (what to run when)
- Proactive planning: `.agents/scripts/session next <session> --with-rules`
- On claim (task to wip): `.agents/scripts/tasks/claim <id> --with-rules`
- On QA creation: `.agents/scripts/qa/new <id> --with-rules`
- Guarded enforcement: `.agents/scripts/tasks/ready`, etc.
```

Also mentions:
- `scripts/rules show <ID>` - Fetch specific rule text
- `scripts/rules require <ID>` - Pull rule snippet for prompts
- `scripts/rules list` - Discover rule IDs

**Post-Edison README.md**:
- ✗ No "Proactive vs Reactive" section
- ✗ No mention of `scripts/session next` workflow loop (CRITICAL for orchestrator!)
- ✗ No mention of `scripts/rules` command
- ✗ No mention of `scripts/tasks/claim`, `scripts/tasks/ready`
- ✗ Only vague reference to "packs" and regenerate commands
- ⚠ Line 135: References `python3 .edison/core/scripts/prompts/compose --all` but this is composition, not session execution

**Pre-Edison explicitly states** (AGENTS.md line 71):
> "Orchestrators MUST load every rule ID referenced by `.agents/scripts/session next` before executing proposed actions"

This workflow loop is MISSING from post-Edison README.md.

**Required Recovery**:
```
Add section to README.md "Session Execution Workflow":
1. Run: scripts/session next <session-id>
2. Read output in order:
   - 📋 APPLICABLE RULES
   - 🎯 RECOMMENDED ACTIONS
   - 🤖 DELEGATION HINT
   - 🔍 VALIDATORS
3. Execute recommended command
4. Repeat step 1

Also add:
- scripts/rules list (discover IDs)
- scripts/rules show <ID> (fetch rule text)
- scripts/tasks/ready (list next tasks)
- scripts/tasks/claim <id> (claim task)
```

---

### GAP #5: Lost Orchestration Scripts Guidance (SEVERITY: MEDIUM)

**Pre-Edison AGENTS.md**:
- Explicit mention of `.agents/scripts/` directory as central command hub
- References to session, rules, qa, tasks, track, validation scripts
- Lines 24-39: "Mandatory Preload" section includes rules/registry.json reference

**Pre-Edison manifest.json** (lines 31-44):
- Session tracking enabled
- Reclaim timeout: 4 hours
- Session record directories: `.project/sessions/{wip,done,validated}`
- Scripts for: `session new|status|complete`, `scripts/tasks/claim`, etc.

**Post-Edison README.md**:
- ✗ No mention of `.agents/scripts/` directory
- ✗ No reference to script commands (session, rules, qa, tasks)
- ✗ Missing orchestration rules from manifest
- ✗ No guidance on session tracking, reclaim timeouts, session records

**Reference in system prompt (at chat start)** mentions:
> "scripts/session next <session-id>" and "scripts/validators/validate <task-id>"

But these are NOT documented in README.md; they appear only in the ORCHESTRATOR_GUIDE.md (generated dynamically).

**Required Recovery**:
```
Add section to README.md "CLI Commands Reference":
1. Session Management:
   - scripts/session next <session-id>
   - scripts/session new
   - scripts/session status <session-id>
   - scripts/session complete <session-id>

2. Task Management:
   - scripts/tasks/ready
   - scripts/tasks/claim <id>
   - scripts/tasks/status <id>

3. QA Management:
   - scripts/qa/new <id>
   - scripts/qa/promote <id>

4. Rules:
   - scripts/rules list
   - scripts/rules show <ID>
   - scripts/rules require <ID>

5. Validation:
   - scripts/validators/validate <task-id>
```

---

## STRUCTURAL DIFFERENCES

### Pre-Edison Architecture (Single Source of Truth)
```
.agents/
├── AGENTS.md                          ← Entry point (110 lines, self-contained)
├── manifest.json                      ← Mandatory preload list + orchestration config
├── session-workflow.json              ← Session state machine
├── START.SESSION.md                   ← Fresh implementation intake
├── START.AUDIT.md                     ← QA/reclaim intake
├── guidelines/
│   ├── SESSION_WORKFLOW.md            ← Active session playbook
│   ├── DELEGATION.md                  ← Model selection
│   ├── TDD.md, CONTEXT7.md, etc.      ← Core framework guidelines (9 files)
├── implementation/
│   ├── IMPLEMENTER_WORKFLOW.md        ← Implementation process
│   └── OUTPUT_FORMAT.md               ← Artifact structure
├── validators/
│   ├── config.json                    ← Validator roster
│   ├── VALIDATOR_WORKFLOW.md          ← Validation process
│   ├── global/, critical/, specialized/
├── agents/
│   ├── api-builder.md
│   ├── component-builder.md
│   ├── ... (6 agents)
├── delegation/
│   └── config.json                    ← Model selection rules
└── scripts/
    ├── session (main orchestration)
    ├── tasks/
    ├── qa/
    ├── rules
    └── validation/
```

**Key feature**: One entry point (AGENTS.md) lists ALL mandatory files in manifest.json.

### Post-Edison Architecture (Distributed Configuration)
```
.agents/
├── README.md                          ← Entry point (295 lines, configuration overview)
├── AGENTS.md                          ← Referenced but role unclear
├── DESIGN.md                          ← Design system (not orchestration)
├── config/
│   ├── defaults.yaml                  ← Edison defaults
│   ├── project.yml                    ← Project overrides
│   ├── delegation.yml                 ← Model selection
│   ├── validators.yml                 ← Validator roster
│   ├── packs.yml                      ← Pack activation
│   ├── commands.yml, hooks.yml, etc.  ← New config files
├── guidelines/
│   ├── wilson-*.md                    ← Project-specific only (8 files, no core guides!)
│   └── overlays/
├── agents/
│   ├── api-builder.md (overlays only)
│   ├── ... (only overlays)
├── validators/
│   ├── *-overlay.md                   ← Project-specific overlays only
├── _generated/
│   ├── agents/
│   ├── validators/
│   ├── guidelines/
│   ├── ORCHESTRATOR_GUIDE.md          ← Generated dynamically
│   └── orchestrator-manifest.json     ← Generated dynamically
└── (no START.SESSION.md, no START.AUDIT.md)

.edison/core/                          ← Framework lives here now
├── guidelines/
│   ├── shared/ (9 core guidelines)
│   ├── agents/ (10 agent guidelines)
│   ├── orchestrators/ (4 orchestrator guidelines)
│   ├── validators/ (4 validator guidelines)
├── validators/
│   └── config.json                    ← Validator specifications
├── delegation/
│   └── config.schema.json             ← Delegation schema
├── packs/ (nextjs, react, prisma, etc.)
└── scripts/
    └── prompts/
        └── compose                    ← Generation script
```

**Key feature**: Configuration is "discovered" dynamically via pack system; no single manifest file.

---

## MANDATORY PRELOAD CHECKLIST COMPARISON

### Pre-Edison (Explicit, Single List)
The pre-Edison manifest.json explicitly lists 19 mandatory files to preload:

1. `.agents/AGENTS.md` - Entry point
2. `.agents/session-workflow.json` - State machine
3. `.agents/guidelines/SESSION_WORKFLOW.md` - Active playbook
4. `.agents/implementation/IMPLEMENTER_WORKFLOW.md` - Implementation process
5. `.agents/validators/VALIDATOR_WORKFLOW.md` - Validation process
6. `.agents/guidelines/HONEST_STATUS.md` - Directory semantics
7. `.agents/guidelines/VALIDATION.md` - QA workflow
8. `.agents/guidelines/QUALITY.md` - Standards
9. `.agents/guidelines/TDD.md` - Test-driven development
10. `.agents/guidelines/CONTEXT7.md` - Package API rules
11. `.agents/guidelines/GIT_WORKFLOW.md` - Git conventions
12. `.agents/guidelines/EPHEMERAL_SUMMARIES_POLICY.md` - Status rules
13. `.agents/guidelines/DELEGATION.md` - Model selection
14. `.agents/implementation/OUTPUT_FORMAT.md` - Artifact structure
15. `.agents/rules/registry.json` - Rule index
16. `.agents/validators/config.json` - Validator roster
17. `.agents/delegation/config.json` - Model rules
18. `.cursor/rules/00-canonical-agents.mdc` - Cursor rules
19. `.cursor/rules/01-validation-guard.mdc` - Validation guard

### Post-Edison (Implicit, Discovered Dynamically)
The post-Edison README.md lists only 3 items under "Quick Start":
1. [AGENTS.md](./AGENTS.md) - Referenced but not found in active directory
2. [TDD Protocol](./guides/TDD_GUIDE.md) - File path doesn't match directory structure
3. [Validation Workflow](./guides/VALIDATION_GUIDE.md) - File path doesn't match directory structure

**Missing from README.md mandatory list**:
- All 19 Edison core guidelines (SESSION_WORKFLOW, DELEGATION, CONTEXT7, etc.)
- Implementation workflow guides
- Validator guides
- Config files (delegation.yml, validators.yml)
- Rule index references
- Cursor rules

---

## MISSING INSTRUCTIONS (DETAILED)

### Category 1: Intake Checklists (2 files, 62 lines)

**PRE-EDISON HAD**:
1. **START.SESSION.md** (35 lines)
   - "Run this checklist at the very beginning of every implementation session"
   - Mandatory preload instruction
   - Explicit intake steps (5 detailed steps)
   - CLI commands: session new, tasks/claim, qa/new
   - Bundle-first rule for validators

2. **START.AUDIT.md** (27 lines)
   - "Launch this prompt only when the human coordinator wants the shared QA + reclaim queues cleared"
   - Mandatory preload instruction
   - Drain qa/todo/, reclaim stale work, audit blockers
   - CLI commands for status, claim, etc.

**POST-EDISON LACKS**:
- ✗ No START.SESSION.md
- ✗ No START.AUDIT.md
- ⚠ README.md section "HOW THE ORCHESTRATOR SHOULD USE" (lines 141-165) is vague:
  - No checklist format
  - No explicit CLI commands (missing: `session new`, `tasks/claim`)
  - No bundle-first rule
  - No reclaim guidance

**Severity**: CRITICAL - New agents cannot orient themselves.

---

### Category 2: Core Framework Guidelines (19 files)

**PRE-EDISON** had all 9 core guidelines in `.agents/guidelines/`:
1. SESSION_WORKFLOW.md - Active session playbook
2. DELEGATION.md - Model selection rules
3. TDD.md - Test-driven development
4. CONTEXT7.md - Package API reference rules
5. VALIDATION.md - QA/validator workflow
6. QUALITY.md - Production standards
7. GIT_WORKFLOW.md - Git conventions
8. EPHEMERAL_SUMMARIES_POLICY.md - Status summary rules
9. HONEST_STATUS.md - Directory semantics

**POST-EDISON** moved these to `.edison/core/guidelines/`:
- ✓ Files exist but are NOT listed in README.md mandatory preload
- ✓ Agents must "discover" them by looking in .edison/core/
- ✗ No explicit link from README.md to these files
- ✗ Pack-specific guidelines (vitest, nextjs, react, etc.) are auto-composed but not manually indexed

**Severity**: HIGH - Agents don't know to preload from .edison/core/.

---

### Category 3: Implementation & Validation Guides (2 files)

**PRE-EDISON HAD**:
1. `.agents/implementation/IMPLEMENTER_WORKFLOW.md` - How implementers should work
2. `.agents/implementation/OUTPUT_FORMAT.md` - Artifact structure requirements
3. `.agents/validators/VALIDATOR_WORKFLOW.md` - How validators should work

**POST-EDISON**:
- ✓ Core equivalents exist in `.edison/core/guidelines/agents/` and `.edison/core/guidelines/validators/`
- ✗ NOT explicitly listed in README.md mandatory preload
- ✗ No guidance to agents on WHERE to find them

**Severity**: MEDIUM - The files exist but aren't navigable from README.md.

---

### Category 4: Configuration & Registry Files (3 files)

**PRE-EDISON HAD**:
1. `.agents/manifest.json` - Centralized orchestration config + preload list
2. `.agents/rules/registry.json` - Rule ID index
3. `.agents/delegation/config.json` - Model selection rules

**POST-EDISON**:
- ✓ `.agents/config/delegation.yml` - Model selection (YAML instead of JSON)
- ✓ `.agents/config/validators.yml` - Validator roster
- ✓ `.edison/core/delegation/config.schema.json` - Delegation schema
- ✓ `.edison/core/validators/config.json` - Validator specifications
- ✗ NO `.agents/manifest.json` at top level
- ✗ NO `.agents/rules/registry.json`
- ✗ NO unified preload list

**Severity**: HIGH - Agents cannot find centralized configuration.

---

### Category 5: Session Execution Workflow (Not Documented)

**PRE-EDISON AGENTS.md** (lines 40-44):
```
Proactive vs Reactive (what to run when)
- Proactive planning: `.agents/scripts/session next <session> --with-rules`
- On claim (task to wip): `.agents/scripts/tasks/claim <id> --with-rules`
- On QA creation: `.agents/scripts/qa/new <id> --with-rules`
- Guarded enforcement: `.agents/scripts/tasks/ready`, ...
```

**POST-EDISON README.md**:
- ✗ NO "session next" workflow loop documented
- ✗ NO explicit CLI command reference section
- ✗ NO "proactive vs reactive" guidance

**System prompt (chat start)** contains:
> "Before EVERY action, run: scripts/session next <session-id>"

But this CRITICAL loop is not documented in README.md.

**Severity**: CRITICAL - Orchestrator workflow is missing from entry point.

---

## SUMMARY TABLE

| Item | Pre-Edison | Post-Edison | Status | Severity |
|------|-----------|-----------|--------|----------|
| Entry Point File | AGENTS.md (110 lines) | README.md (295 lines) | MODIFIED | - |
| START.SESSION.md | ✓ 35 lines | ✗ MISSING | CRITICAL GAP | CRITICAL |
| START.AUDIT.md | ✓ 27 lines | ✗ MISSING | CRITICAL GAP | CRITICAL |
| manifest.json | ✓ Centralized | ✗ Distributed (YAML) | STRUCTURAL CHANGE | HIGH |
| Mandatory preload list | ✓ 19 items in manifest | ✗ Only 3 in README | INCOMPLETE | CRITICAL |
| Core guidelines (9) | ✓ .agents/guidelines/ | ✓ .edison/core/guidelines/ | MOVED | HIGH |
| START checklist | ✓ Both files | ✗ None | MISSING | CRITICAL |
| CLI workflow (session next) | ✓ Documented | ✗ Not in README | MISSING | CRITICAL |
| scripts/ guidance | ✓ Full reference | ✗ No section | MISSING | MEDIUM |
| Delegation rules | ✓ config.json | ✓ delegation.yml | FORMAT CHANGE | LOW |
| Rule registry | ✓ rules/registry.json | ✗ Not found | MISSING | MEDIUM |

---

## RECOVERY RECOMMENDATIONS

### Immediate Actions (Restore CRITICAL functionality)

1. **Restore START.SESSION.md**
   - Copy from pre-Edison: `/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/START.SESSION.md`
   - Location: `/Users/leeroy/Documents/Development/wilson-leadgen/.agents/START.SESSION.md`
   - Update paths to reference `.edison/core/guidelines/` where appropriate

2. **Restore START.AUDIT.md**
   - Copy from pre-Edison: `/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/START.AUDIT.md`
   - Location: `/Users/leeroy/Documents/Development/wilson-leadgen/.agents/START.AUDIT.md`
   - Update paths to reference `.edison/core/guidelines/` where appropriate

3. **Create .agents/manifest.json**
   - Purpose: Centralized preload list for agents
   - Content: Update pre-Edison manifest to point to new locations:
     - Guidelines: `.edison/core/guidelines/shared/*`, `.agents/guidelines/*`
     - Validators: `.agents/config/validators.yml`, `.edison/core/validators/config.json`
     - Delegation: `.agents/config/delegation.yml`, `.edison/core/delegation/config.schema.json`
   - Structure: Keep JSON format for machine parsing

4. **Update .agents/README.md**
   - Add section: "Mandatory Preloads (Session Start)" with complete 19-item list
   - Add section: "Session Execution Workflow" with `scripts/session next` loop
   - Add section: "CLI Commands Reference" (session, rules, tasks, qa, validators)
   - Add explicit links to START.SESSION.md and START.AUDIT.md
   - Add table of .edison/core/guidelines/ files with descriptions

### Secondary Actions (Improve Navigation)

5. **Create .agents/QUICK_START.md** (New)
   - Purpose: Quick reference for first-time agents
   - Content:
     - 10-item checklist before touching code
     - 5 essential CLI commands
     - 3 example workflows (parallel, sequential, focused)
     - Links to mandatory files

6. **Create/Update .agents/rules/registry.json**
   - Purpose: Rule ID index (like pre-Edison)
   - Content: All rules referenced in guidelines (RULE.CONTEXT.*, RULE.DELEGATION.*, etc.)

7. **Add .agents/ARCHITECTURE.md**
   - Purpose: Explain pre-Edison vs post-Edison migration
   - Content:
     - Why: Edison framework introduction
     - What moved: .agents/ to .edison/core/, config to YAML, generation system
     - How to navigate: .agents/ (project-specific) vs .edison/core/ (framework)
     - Backward compatibility notes

### Validation Checklist

Before closing this gap analysis:

- [ ] START.SESSION.md exists at `.agents/START.SESSION.md`
- [ ] START.AUDIT.md exists at `.agents/START.AUDIT.md`
- [ ] .agents/manifest.json exists with 19+ mandatory items
- [ ] README.md mandatory preload list has 19+ items
- [ ] README.md explains where .edison/core/guidelines/ files are
- [ ] README.md documents `scripts/session next` workflow
- [ ] README.md has CLI commands reference section
- [ ] All 9 Edison core guidelines are reachable from README.md

---

## CONCLUSION

The post-Edison architecture successfully moves to a composable, pack-based system with distributed configuration. However, **the entry point documentation has regressed significantly**:

**Before (Pre-Edison)**:
- Single entry point (AGENTS.md)
- Explicit mandatory preload list (manifest.json)
- Two intake checklists (START.SESSION.md, START.AUDIT.md)
- Complete CLI workflow documentation

**After (Post-Edison)**:
- Distributed configuration (YAML files across .agents/ and .edison/core/)
- Implicit mandatory list (not documented in README.md)
- No intake checklists
- No CLI workflow documentation in entry point
- Generated artifacts (ORCHESTRATOR_GUIDE.md) appear only in orchestrator context, not in README.md

**Risk**: New agents (or agents with context loss) cannot self-orient. They will:
1. Not know which files are mandatory (only 3 listed instead of 19+)
2. Not have intake checklists to follow
3. Not understand the `scripts/session next` workflow
4. Get lost between .agents/ and .edison/core/ directories

**Recommendation**: Restore the intake checklists and update README.md to list all mandatory files and document the session workflow loop. This ensures backward compatibility while leveraging the new Edison system.

---

**Validation completed**: 2025-11-25T11:45:00Z
**Validator**: Claude Code Agent
**Files analyzed**: 12
**Total gap items**: 5 CRITICAL, 3 HIGH, 2 MEDIUM
