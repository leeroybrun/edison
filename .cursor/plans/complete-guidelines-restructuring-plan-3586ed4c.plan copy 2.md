<!-- 3586ed4c-83d4-402b-b34c-42118219eed2 3966a05a-747e-4586-b715-0e888188f218 -->
# Complete Guidelines Restructuring with Templating Engine

## Executive Summary

This plan addresses four critical issues using Edison's templating system:

1. **Duplicated content** across packs/agents/validators → Use canonical source files with `{{include-section:...}}`
2. **Role-specific content loaded by wrong roles** → Use named sections per role, include only what's needed
3. **Double-loading** (content both included AND mandatory read) → Content is EITHER embedded via include OR referenced, never both
4. **Hardcoded dynamic content** → Use `{{fn:...}}` functions for state machine, rosters, versions

---

## PART A: TEMPLATING STRATEGY (NEW APPROACH)

### A1. Core Principle: Include vs Reference

**CRITICAL RULE**: Content should be EITHER included (embedded) OR referenced (mandatory read), NEVER BOTH.

| Strategy | When to Use | Result |

|----------|-------------|--------|

| `{{include:path}}` | Critical rules that MUST be in prompt | Content embedded in composed file |

| `{{include-section:path#section}}` | Role-specific portions of shared files | Only relevant section embedded |

| Mandatory Read reference | Deep-dive docs for on-demand reading | Agent reads separately when needed |

**Anti-pattern to ELIMINATE**:

```markdown
## Mandatory Preloads
- shared/TDD.md  ← Lists file to read

## TDD Protocol
{{include:shared/TDD.md}}  ← ALSO includes same file

# RESULT: Agent reads TDD.md TWICE - wastes context!
```

### A2. Canonical Source Files with Named Sections

Create canonical files with role-specific sections that different roles include:

```markdown
# guidelines/developer/TDD.md (CANONICAL SOURCE)

<!-- SECTION: principles -->
## TDD Principles (Universal)
- RED: Write failing test first
- GREEN: Minimal implementation
- REFACTOR: Clean up
<!-- /SECTION: principles -->

<!-- SECTION: agent-execution -->
## TDD Execution (Agent Guide)
[How agents actually DO TDD - create tests, run them, etc.]
<!-- /SECTION: agent-execution -->

<!-- SECTION: validator-check -->
## TDD Compliance Check (Validator Guide)
[How validators CHECK that TDD was followed]
<!-- /SECTION: validator-check -->

<!-- SECTION: orchestrator-verify -->
## TDD Verification (Orchestrator Guide)
[How orchestrators VERIFY TDD compliance before approval]
<!-- /SECTION: orchestrator-verify -->
```

**Usage in role files**:

```markdown
# agents/feature-implementer.md
## TDD Protocol
{{include-section:guidelines/developer/TDD.md#principles}}
{{include-section:guidelines/developer/TDD.md#agent-execution}}
# Validator/orchestrator sections NOT included - saves context!
```

### A3. Functions for Dynamic Content

**DO NOT hardcode** state machine states, validator rosters, package versions.

| Content | Function | Usage |

|---------|----------|-------|

| Task states | `{{fn:task_states}}` | Returns current task states from config |

| QA states | `{{fn:qa_states}}` | Returns current QA states from config |

| Transitions | `{{fn:state_transitions domain}}` | Returns valid transitions |

| Package versions | `{{config.context7.packages.*.version}}` | From YAML config |

| Validator roster | `{{#each validators}}` | Loop over config |

**Create new functions** in `src/edison/data/functions/`:

```python
# state_machine.py
def task_states() -> str:
    """Return task states from config as markdown list."""
    # Load from state machine config, not hardcoded
    
def qa_states() -> str:
    """Return QA states from config as markdown list."""

def state_transitions(domain: str = "task") -> str:
    """Return valid transitions for domain as markdown table."""
```

### A4. Pack-Conditional Content

Use `{{if:has-pack(name)}}` for technology-specific content:

```markdown
# agents/test-engineer.md

## Testing Frameworks
{{if:has-pack(python)}}
### Python Testing (pytest)
{{include-section:packs/python/guidelines/TESTING.md#pytest-patterns}}
{{/if}}

{{if:has-pack(vitest)}}
### JavaScript Testing (Vitest)
{{include-section:packs/vitest/guidelines/TESTING.md#vitest-patterns}}
{{/if}}
```

---

## PART B: ROLE ANALYSIS - Who Needs What

### B1. ORCHESTRATOR-ONLY Content

| Content | Current Location | Action |

|---------|------------------|--------|

| Session management | `orchestrators/SESSION_WORKFLOW.md` | KEEP isolated |

| Delegation decisions | `orchestrators/DELEGATION.md` | KEEP isolated |

| Validator wave orchestration | `shared/VALIDATION.md` | MOVE to `orchestrators/VALIDATOR_ORCHESTRATION.md` |

| Bundle approval | `shared/VALIDATION.md` | MOVE to orchestrator section |

| TDD verification checklists | `shared/TDD.md` | MOVE to `TDD.md#orchestrator-verify` section |

| Parent/child orchestration | `shared/VALIDATION.md` | MOVE to orchestrator section |

### B2. AGENT-ONLY Content

| Content | Current Location | Action |

|---------|------------------|--------|

| Claim-Implement-Ready | `agents/MANDATORY_WORKFLOW.md` | KEEP - include in agents |

| Implementation report | `agents/OUTPUT_FORMAT.md` | KEEP - include in agents |

| TDD execution | `shared/TDD.md` | MOVE to `TDD.md#agent-execution` section |

| Evidence creation | scattered | CONSOLIDATE to `TDD.md#agent-execution` |

### B3. VALIDATOR-ONLY Content

| Content | Current Location | Action |

|---------|------------------|--------|

| Validation workflow | `validators/VALIDATOR_WORKFLOW.md` | KEEP isolated |

| Verdict rules | `validators/VALIDATOR_COMMON.md` | KEEP isolated |

| TDD compliance check | validators + shared | MOVE to `TDD.md#validator-check` section |

| Evidence verification | scattered | CONSOLIDATE to validator section |

### B4. TRULY SHARED Content (Minimal)

| Content | Action |

|---------|--------|

| Context7 query workflow | KEEP in `shared/CONTEXT7.md` - include section-by-role |

| Core principles | CREATE canonical `shared/PRINCIPLES.md` with sections |

| State machine | USE `{{fn:task_states}}` `{{fn:qa_states}}` - NO hardcoded file |

---

## PART C: CANONICAL SOURCE FILE STRUCTURE

### C1. Developer Guidelines (Shared by Agents + Validators)

```
guidelines/developer/
├── TDD.md                    # CANONICAL - with role sections
│   ├── <!-- SECTION: principles -->     # All roles
│   ├── <!-- SECTION: agent-execution --> # Agents only
│   ├── <!-- SECTION: validator-check --> # Validators only
│   └── <!-- SECTION: orchestrator-verify --> # Orchestrators only
│
├── NO_MOCKS_POLICY.md        # CANONICAL - with role sections
│   ├── <!-- SECTION: philosophy -->     # All roles
│   ├── <!-- SECTION: implementation --> # Agents: how to avoid mocks
│   └── <!-- SECTION: validation -->     # Validators: what to flag
│
├── TYPE_SAFETY.md            # CANONICAL
│   ├── <!-- SECTION: principles -->
│   ├── <!-- SECTION: implementation -->
│   └── <!-- SECTION: validation -->
│
├── ERROR_HANDLING.md         # CANONICAL
├── CONFIGURATION_FIRST.md    # CANONICAL
├── TEST_ISOLATION.md         # CANONICAL
└── ACCESSIBILITY.md          # CANONICAL
```

### C2. Role-Specific Files (Use Includes)

```
guidelines/
├── agents/
│   ├── COMMON.md             # {{include-section:...}} from developer/*
│   ├── MANDATORY_WORKFLOW.md # Agent-specific, no sections needed
│   └── OUTPUT_FORMAT.md      # Agent-specific
│
├── validators/
│   ├── VALIDATOR_COMMON.md   # {{include-section:...}} from developer/*
│   ├── VALIDATOR_WORKFLOW.md # Validator-specific
│   └── OUTPUT_FORMAT.md      # Validator-specific
│
└── orchestrators/
    ├── SESSION_WORKFLOW.md   # Orchestrator-specific
    ├── DELEGATION.md         # Orchestrator-specific
    └── VALIDATOR_ORCHESTRATION.md # Moved from shared/VALIDATION.md
```

---

## PART D: CONSTITUTION REDESIGN

### D1. New Constitution Pattern

**OLD (Double-loading)**:

```markdown
## Mandatory Preloads
- TDD.md
- QUALITY.md
- CONTEXT7.md
...

## TDD Protocol
[Brief summary that duplicates TDD.md content]
```

**NEW (Single-loading via includes)**:

```markdown
# constitutions/agents-base.md

## Core Principles
{{include-section:guidelines/shared/PRINCIPLES.md#agent-principles}}

## TDD Protocol
{{include-section:guidelines/developer/TDD.md#principles}}
{{include-section:guidelines/developer/TDD.md#agent-execution}}

## Testing Philosophy
{{include-section:guidelines/developer/NO_MOCKS_POLICY.md#philosophy}}
{{include-section:guidelines/developer/NO_MOCKS_POLICY.md#implementation}}

## Context7 Usage
{{include-section:guidelines/shared/CONTEXT7.md#workflow}}

## Deep-Dive References (Read On-Demand)
- `guidelines/shared/QUALITY.md` - Extended code quality patterns
- `guidelines/shared/GIT_WORKFLOW.md` - Git conventions
```

### D2. Constitution Content Allocation

| Content Type | Strategy | Rationale |

|--------------|----------|-----------|

| Critical rules (TDD, NO_MOCKS) | `{{include-section:...}}` | MUST be in prompt, cannot be missed |

| Workflow steps | `{{include-section:...}}` | Agent needs these immediately |

| Code examples | Reference only | Load on-demand, saves context |

| Deep patterns | Reference only | Use when facing specific issues |

---

## PART E: PACK REDESIGN

### E1. Pack Guidelines Pattern

**OLD (Duplicated generic content)**:

```markdown
# packs/python/guidelines/TESTING.md
## NO MOCKS POLICY
[50 lines duplicating shared/NO_MOCKS_POLICY.md]

## Python Testing
[Python-specific content]
```

**NEW (Include generic, keep specific)**:

```markdown
# packs/python/guidelines/TESTING.md

## Testing Philosophy
{{include-section:guidelines/developer/NO_MOCKS_POLICY.md#philosophy}}

## Test Isolation
{{include-section:guidelines/developer/TEST_ISOLATION.md#principles}}

<!-- SECTION: pytest-patterns -->
## Python-Specific: pytest Patterns
[ONLY Python-specific pytest content here]
<!-- /SECTION: pytest-patterns -->

<!-- SECTION: tmp-path -->
## Python-Specific: tmp_path Usage
[ONLY tmp_path patterns]
<!-- /SECTION: tmp-path -->
```

### E2. Pack Validator Overlays Pattern

```markdown
# packs/python/validators/overlays/global.md

<!-- EXTEND: TechStack -->
## Python Validation Context

### Generic Checks (Included)
{{include-section:guidelines/developer/TYPE_SAFETY.md#validation}}
{{include-section:guidelines/developer/NO_MOCKS_POLICY.md#validation}}

### Python-Specific Checks
- mypy --strict must pass
- ruff check must pass
- pytest with no mocks
<!-- /EXTEND -->
```

---

## PART F: AGENT FILE REDESIGN

### F1. Agent Pattern

**OLD (Embedded duplicates)**:

```markdown
# agents/feature-implementer.md

## TDD Protocol (MANDATORY)
- RED: Write tests first
- GREEN: Implement
- REFACTOR: Clean up
[30 lines duplicating TDD.md]

## Context7 (MANDATORY)
[30 lines duplicating CONTEXT7.md]
```

**NEW (Sections + Includes)**:

```markdown
# agents/feature-implementer.md
---
name: feature-implementer
...
---

## Constitution Awareness
{{include-section:constitutions/agents-base.md#binding-rules}}

## TDD Protocol
{{include-section:guidelines/developer/TDD.md#principles}}
{{include-section:guidelines/developer/TDD.md#agent-execution}}

## Context7 Knowledge Refresh
{{include-section:guidelines/shared/CONTEXT7.md#workflow}}

<!-- SECTION: tools -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tools -->

<!-- SECTION: guidelines -->
## Feature Implementation Guidelines
[ONLY feature-implementer specific content]
<!-- /SECTION: guidelines -->

{{if:has-pack(python)}}
## Python-Specific
{{include-section:packs/python/agents/overlays/feature-implementer.md#python-tools}}
{{/if}}

{{if:has-pack(react)}}
## React-Specific
{{include-section:packs/react/agents/overlays/feature-implementer.md#react-tools}}
{{/if}}
```

---

## PART G: FUNCTIONS TO CREATE

### G1. State Machine Functions

```python
# src/edison/data/functions/state_machine.py

def task_states() -> str:
    """Return task states as markdown list from config."""
    # Load from STATE_MACHINE.md or config, NOT hardcoded
    
def qa_states() -> str:
    """Return QA states as markdown list from config."""

def task_transitions() -> str:
    """Return task state transitions as markdown table."""

def qa_transitions() -> str:
    """Return QA state transitions as markdown table."""

def state_diagram(domain: str = "task") -> str:
    """Return mermaid diagram for state machine."""
```

### G2. Guidelines Helper Functions

```python
# src/edison/data/functions/guidelines.py

def developer_guidelines() -> str:
    """Return list of developer guidelines with paths."""

def role_guidelines(role: str) -> str:
    """Return guidelines relevant for role (agent/validator/orchestrator)."""
```

---

## PART H: VALIDATION.md AND TDD.md SPLITS

### H1. shared/VALIDATION.md → Minimal Overview

**KEEP only** (~30 lines):

- What validation is (concept)
- Verdict types (approve/reject/blocked)
- Reference to role-specific files

**MOVE orchestration content** to `orchestrators/VALIDATOR_ORCHESTRATION.md`:

- Wave execution
- Bundle management
- Parallel validation
- CLI commands for orchestration

**MOVE validator content** to `validators/VALIDATION_EXECUTION.md`:

- How validators load bundles
- How validators write reports
- Follow-up creation rules

### H2. shared/TDD.md → Sectioned Canonical File

**Restructure as sections**:

```markdown
# guidelines/developer/TDD.md

<!-- SECTION: principles -->
## TDD Principles (All Roles)
- RED-GREEN-REFACTOR concept
- Core rules
- Guardrails (.skip/.todo forbidden)
<!-- /SECTION: principles -->

<!-- SECTION: agent-execution -->
## TDD Execution (Agents)
- How to write failing tests first
- Evidence file creation
- Commit tag usage
<!-- /SECTION: agent-execution -->

<!-- SECTION: validator-check -->
## TDD Compliance (Validators)
- What to verify in git history
- Red flags to catch
- How to report violations
<!-- /SECTION: validator-check -->

<!-- SECTION: orchestrator-verify -->
## TDD Verification (Orchestrators)
- Verification checklist
- Delegation templates
- Report template
<!-- /SECTION: orchestrator-verify -->
```

---

## PART I: MIGRATION PHASES

### Phase 1: Create Functions

1. Create `src/edison/data/functions/state_machine.py`
2. Create `src/edison/data/functions/guidelines.py`
3. Update `tasks_states.py` to read from config (not hardcoded list)
4. Test functions work in templates

### Phase 2: Create Canonical Developer Guidelines

5. Create `guidelines/developer/TDD.md` with role sections
6. Create `guidelines/developer/NO_MOCKS_POLICY.md` with role sections
7. Create `guidelines/developer/TYPE_SAFETY.md` with role sections
8. Create `guidelines/developer/ERROR_HANDLING.md`
9. Create `guidelines/developer/CONFIGURATION_FIRST.md`
10. Create `guidelines/developer/TEST_ISOLATION.md` with role sections
11. Create `guidelines/developer/ACCESSIBILITY.md`

### Phase 3: Restructure Shared Guidelines

12. Slim `shared/TDD.md` - keep only principles, reference developer/TDD.md
13. Slim `shared/VALIDATION.md` - keep only overview
14. Create `orchestrators/VALIDATOR_ORCHESTRATION.md` from VALIDATION.md content
15. Create `validators/VALIDATION_EXECUTION.md` from VALIDATION.md content
16. Remove `shared/STATE_MACHINE_OVERVIEW.md` - use functions instead

### Phase 4: Update Packs to Use Includes

17. Update Python pack - replace duplicates with `{{include-section:...}}`
18. Update Vitest pack - replace duplicates with includes
19. Update React pack - replace duplicates with includes
20. Update remaining packs (Prisma, NextJS, Tailwind, TypeScript)

### Phase 5: Update Agents to Use Includes

21. Update `feature-implementer.md` - use includes, add pack conditionals
22. Update `test-engineer.md` - use includes
23. Update `code-reviewer.md` - use includes
24. Update `python-developer.md` - use includes
25. Update all other agents

### Phase 6: Update Validators to Use Includes

26. Update `VALIDATOR_COMMON.md` - use includes from developer/*
27. Update pack validator overlays - use includes

### Phase 7: Redesign Constitutions

28. Update `agents-base.md` - embed critical content via includes, reference deep-dives
29. Update `validators-base.md` - same pattern
30. Update `orchestrator-base.md` - same pattern
31. Remove double-loaded content from mandatory reads

### Phase 8: Validate and Test

32. Run `edison compose --all`
33. Verify no broken includes/sections
34. Compare composed output sizes (should be smaller per role)
35. Test agent/validator/orchestrator with real tasks
36. Verify no duplicate content in composed outputs

---

## PART J: SUCCESS METRICS

| Metric | Before | Target |

|--------|--------|--------|

| Duplicated lines in source | ~2000 | 0 |

| Agent context size | ~1500 lines | ~800 lines |

| Validator context size | ~1200 lines | ~600 lines |

| Orchestrator context size | ~1800 lines | ~1000 lines |

| Files to update when TDD rules change | ~15 | 1 (canonical) |

| Double-loaded content | Present | Zero |

| Hardcoded state machine | Present | Zero (functions) |

---

## PART K: KEY PRINCIPLES SUMMARY

1. **Single Source of Truth**: Each rule/guideline lives in ONE canonical file with sections
2. **Include, Don't Duplicate**: Use `{{include-section:...}}` instead of copy-paste
3. **Role-Specific Sections**: Each canonical file has sections for agent/validator/orchestrator
4. **No Double-Loading**: Content is EITHER included OR referenced, never both
5. **Functions for Dynamic**: State machine, versions, rosters come from functions/config
6. **Pack-Conditional**: Use `{{if:has-pack(...)}}` for technology-specific content
7. **Composed Duplication OK**: Final composed files CAN have duplicated content (from includes) - source files must NOT

### To-dos

- [ ] Phase 1: Create state_machine.py and guidelines.py functions
- [ ] Phase 1: Update tasks_states.py to read from config not hardcoded
- [ ] Phase 2: Create guidelines/developer/TDD.md with role sections (principles, agent-execution, validator-check, orchestrator-verify)
- [ ] Phase 2: Create guidelines/developer/NO_MOCKS_POLICY.md with role sections
- [ ] Phase 2: Create guidelines/developer/TYPE_SAFETY.md with role sections
- [ ] Phase 2: Create ERROR_HANDLING.md, CONFIGURATION_FIRST.md, TEST_ISOLATION.md, ACCESSIBILITY.md
- [ ] Phase 3: Slim shared/TDD.md and shared/VALIDATION.md to minimal overviews
- [ ] Phase 3: Create orchestrators/VALIDATOR_ORCHESTRATION.md from VALIDATION.md
- [ ] Phase 3: Create validators/VALIDATION_EXECUTION.md from VALIDATION.md
- [ ] Phase 4: Update Python pack to use {{include-section:...}} for generic content
- [ ] Phase 4: Update Vitest pack to use includes
- [ ] Phase 4: Update React pack to use includes
- [ ] Phase 4: Update remaining packs (Prisma, NextJS, Tailwind, TypeScript)
- [ ] Phase 5: Update all agent files to use includes and pack conditionals
- [ ] Phase 6: Update VALIDATOR_COMMON.md and pack overlays to use includes
- [ ] Phase 7: Redesign constitutions - embed via includes, remove double-loading
- [ ] Phase 8: Run edison compose, verify sizes reduced, test with real tasks