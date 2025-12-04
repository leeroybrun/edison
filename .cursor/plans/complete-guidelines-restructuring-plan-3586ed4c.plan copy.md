<!-- 3586ed4c-83d4-402b-b34c-42118219eed2 5ccea8f6-d5c7-4ac7-bf3e-3d507cf4f51d -->
# Complete Guidelines Restructuring Plan

## Executive Summary

This plan addresses three critical issues:

1. **Duplicated content** across packs/agents/validators
2. **Role-specific content loaded by wrong roles** (context bloat)
3. **Generic developer guidelines embedded instead of referenced**

---

## PART A: ROLE ANALYSIS - Who Needs What

### A1. ORCHESTRATOR-ONLY Content (Should NOT be loaded by agents/validators)

| Content | Current Location | Issue |

|---------|------------------|-------|

| Delegation decisions (who to assign) | `orchestrators/DELEGATION.md` | OK - already isolated |

| Session management (worktree, states) | `orchestrators/SESSION_WORKFLOW.md` | OK - already isolated |

| Validator wave orchestration | `shared/VALIDATION.md` | **MOVE** - orchestrator-only |

| Concurrency management | `orchestrators/SESSION_WORKFLOW.md` | OK |

| Bundle approval decisions | `shared/VALIDATION.md` | **MOVE** - orchestrator-only |

| TDD verification checklists | `shared/TDD.md` | **MOVE** - orchestrator-only |

| Delegation templates for sub-agents | `shared/TDD.md` | **MOVE** - orchestrator-only |

| Follow-up linking decisions | `orchestrators/SESSION_WORKFLOW.md` | OK |

| Parent/child task orchestration | `shared/VALIDATION.md` | **MOVE** - orchestrator-only |

### A2. AGENT-ONLY Content (Should NOT be loaded by orchestrators/validators)

| Content | Current Location | Issue |

|---------|------------------|-------|

| Claim-Implement-Ready workflow | `agents/MANDATORY_WORKFLOW.md` | OK |

| Implementation report format | `agents/OUTPUT_FORMAT.md` | OK |

| TDD execution details (RED-GREEN-REFACTOR how-to) | `shared/TDD.md` + packs | **SPLIT** - agent-only execution |

| MISMATCH pattern for scope issues | `agents/DELEGATION_AWARENESS.md` | OK |

| Code patterns/examples (Python, React, etc.) | packs | OK |

| Type hint execution details | packs | OK |

| Testing pattern execution | packs | OK |

| Evidence file creation (command-*.txt) | `agents/MANDATORY_WORKFLOW.md` | OK |

| Context7 evidence marker creation | scattered | **CONSOLIDATE** |

### A3. VALIDATOR-ONLY Content (Should NOT be loaded by orchestrators/agents)

| Content | Current Location | Issue |

|---------|------------------|-------|

| Validation workflow (Intake→Verdict) | `validators/VALIDATOR_WORKFLOW.md` | OK |

| Verdict determination rules | `validators/VALIDATOR_COMMON.md` | OK |

| Validator independence rules | `validators/VALIDATOR_COMMON.md` | OK |

| Validator report format | `validators/OUTPUT_FORMAT.md` | OK |

| Escalation to global validator | `validators/VALIDATOR_COMMON.md` | OK |

| Evidence checking (what to verify) | `validators/VALIDATOR_COMMON.md` | **DUPLICATED** with packs |

| Bundle validation rules | `shared/VALIDATION.md` | **SPLIT** - validator portion |

### A4. TRULY SHARED Content (All 3 roles need)

| Content | Current Location | Action |

|---------|------------------|--------|

| Context7 query workflow | `shared/CONTEXT7.md` | KEEP shared |

| State machine (task/QA states) | generated dynamically | USE template functions `{{fn:task_states}}` `{{fn:qa_states}}` - NO hardcoded states |

| Core principles (high-level) | `.cursor/rules/rules.mdc` | CREATE `shared/PRINCIPLES.md` |

| Edison CLI overview | scattered | CREATE `shared/EDISON_CLI_OVERVIEW.md` |

---

## PART B: DUPLICATED CONTENT ANALYSIS

### B1. NO_MOCKS_POLICY - Currently Duplicated In:

```
packs/python/guidelines/python/TESTING.md        [~50 lines]
  - "NO MOCKS EVER" section
  - Python-specific mock alternatives

packs/python/agents/python-developer.md          [~20 lines]
  - "Testing Patterns (NO MOCKS)"

packs/python/validators/python.md                [~15 lines]
  - "NO MOCKS rule" check

packs/vitest/validators/testing.md               [~80 lines]
  - "Realistic Tests (Minimal Mocking)"
  - Full mock vs real behavior examples

packs/vitest/guidelines/vitest/TESTING.md        [~20 lines]
  - "No-Mock Policy (Critical Paths)"

guidelines/shared/QUALITY.md                     [~15 lines]
  - "No-Mock Policy" section

agents/feature-implementer.md                    [~10 lines]
agents/test-engineer.md                          [~10 lines]
agents/code-reviewer.md                          [~5 lines]
```

**Action**: Extract to `guidelines/developer/NO_MOCKS_POLICY.md` (~100 lines total)

### B2. TDD PRINCIPLES - Currently Duplicated In:

```
guidelines/shared/TDD.md                         [~297 lines]
  - RED-GREEN-REFACTOR cycle
  - Evidence requirements
  - Commit tags
  - TDD verification (ORCHESTRATOR-ONLY)
  - Delegation templates (ORCHESTRATOR-ONLY)

packs/python/guidelines/python/TESTING.md        [~60 lines]
  - "TDD Workflow" section

packs/vitest/guidelines/vitest/tdd-workflow.md   [~7 lines]
  - Brief TDD summary

agents/feature-implementer.md                    [~30 lines]
agents/test-engineer.md                          [~50 lines]
agents/python-developer.md                       [~40 lines]

validators/testing.md                            [~100 lines]
  - TDD compliance checking
```

**Action**:

1. Keep `shared/TDD.md` for universal principles (~50 lines)
2. Create `agents/TDD_EXECUTION.md` for agent execution details (~100 lines)
3. Create `orchestrators/TDD_VERIFICATION.md` for orchestrator verification (~150 lines)
4. Create `validators/TDD_COMPLIANCE_CHECK.md` for validator checks (~50 lines)

### B3. TYPE_SAFETY - Currently Duplicated In:

```
packs/python/guidelines/python/TYPING.md         [~523 lines]
  - Full Python typing guide

packs/python/validators/python.md                [~50 lines]
  - "Type Safety (BLOCKING)" check

packs/typescript/guidelines/typescript/type-safety.md [~7 lines]
  - Brief TS patterns

validators/react.md                              [~20 lines]
  - Type checking references
```

**Action**:

1. Create `guidelines/developer/TYPE_SAFETY_PRINCIPLES.md` (~50 lines) - generic
2. Keep language-specific details in packs (Python/TypeScript)

### B4. ERROR_HANDLING - Currently Duplicated In:

```
packs/python/guidelines/python/PYTHON.md         [~50 lines]
  - Domain exception hierarchy
  - Specific vs bare exception

packs/python/validators/python.md                [~30 lines]
  - Error handling checks

packs/nextjs/agents/overlays/api-builder.md      [~40 lines]
  - Error Handling Pattern (Next.js)

agents/feature-implementer.md                    [~10 lines]
  - Error handling requirements
```

**Action**: Create `guidelines/developer/ERROR_HANDLING.md` (~60 lines)

### B5. CONFIGURATION_FIRST - Currently Duplicated In:

```
packs/python/guidelines/python/PYTHON.md         [~40 lines]
  - "Configuration" section

packs/python/validators/python.md                [~30 lines]
  - "Configuration (NO HARDCODING)"

guidelines/shared/SHARED_COMMON.md               [~10 lines]
  - "Configuration-First Guardrail"

agents/feature-implementer.md                    [~15 lines]
  - "CONFIG-DRIVEN" rule
```

**Action**: Create `guidelines/developer/CONFIGURATION_FIRST.md` (~50 lines)

### B6. TEST_ISOLATION - Currently Duplicated In:

```
packs/vitest/validators/testing.md               [~60 lines]
  - "Test Isolation" section

packs/vitest/guidelines/vitest/TESTING.md        [~40 lines]
  - Physical/Logical Isolation

packs/prisma/guidelines/prisma/TESTING.md        [~50 lines]
  - Template pool pattern

guidelines/shared/TDD.md                         [~30 lines]
  - "Committed Data + Unique IDs"
```

**Action**: Create `guidelines/developer/TEST_ISOLATION.md` (~80 lines)

### B7. ACCESSIBILITY - Currently Duplicated In:

```
packs/react/validators/react.md                  [~80 lines]
  - Full accessibility section

guidelines/shared/QUALITY.md                     [~30 lines]
  - "Accessibility (WCAG AA)"

agents/feature-implementer.md                    [~10 lines]
  - "Accessibility (WCAG AA)"
```

**Action**: Create `guidelines/developer/ACCESSIBILITY.md` (~60 lines)

### B8. CODE_QUALITY - Currently Duplicated In:

```
guidelines/shared/QUALITY.md                     [~248 lines]
  - Code smell checklist
  - Quality checklist

validators/VALIDATOR_COMMON.md                   [~100 lines]
  - Code quality checks

packs/python/validators/python.md                [~50 lines]
  - Python code quality

packs/react/validators/react.md                  [~40 lines]
  - React code quality
```

**Action**: Consolidate into enhanced `guidelines/shared/QUALITY.md`, reference from validators

### B9. CONTEXT7 USAGE - Currently Duplicated In:

```
guidelines/shared/CONTEXT7.md                    [~57 lines]
guidelines/shared/SHARED_COMMON.md               [~20 lines]
agents/feature-implementer.md                    [~30 lines]
agents/test-engineer.md                          [~30 lines]
agents/code-reviewer.md                          [~30 lines]
validators/testing.md                            [~20 lines]
validators/react.md                              [~15 lines]
```

**Action**: Keep single `shared/CONTEXT7.md`, remove duplicates from agents/validators

---

## PART C: VALIDATION.md SPLIT

Current `shared/VALIDATION.md` contains mixed content:

### C1. Content to KEEP in shared (all roles reference):

- Validation Checklist overview (~20 lines)
- Wave definitions (what they are, not how to orchestrate)
- Verdict types (approve/reject/blocked)

### C2. Content to MOVE to `orchestrators/VALIDATOR_ORCHESTRATION.md`:

- "Validator Roster & Waves" orchestration details
- "Batched Parallel Execution Model"
- "Wave Execution Order" diagram
- "Bundle-first rule"
- "Bundle approval marker"
- "Sequence (strict order)"
- "Parent vs Child Tasks (Parallel Implementation)"
- "CLI Helpers" for orchestrators

### C3. Content to MOVE to `validators/VALIDATION_EXECUTION.md`:

- How validators load the bundle
- How validators write reports
- Validator follow-up creation rules

---

## PART D: TDD.md SPLIT

Current `shared/TDD.md` contains mixed content:

### D1. Content to KEEP in shared (universal principles):

- "TDD Checklist" (high-level)
- "RED-GREEN-REFACTOR Cycle" (concept)
- "Core Rules" (high-level)
- "Guardrails" (.skip/.todo)
- "TDD Troubleshooting" (universal)
- "Commit Tag Requirements"

### D2. Content to MOVE to `orchestrators/TDD_VERIFICATION.md`:

- "TDD Verification Checklist - For Orchestrator"
- "TDD Verification Report Template"
- "Red Flags (TDD Violations)"
- "TDD When Delegating to Sub-Agents"
- All delegation templates (Component Builder, API Builder, Database Architect)

### D3. Content to MOVE to `agents/TDD_EXECUTION.md`:

- "Patterns" section (Committed Data + Unique IDs, PostgreSQL Template Pool)
- "Evidence Requirements" (how agents create evidence)

---

## PART E: NEW FILE STRUCTURE

```
guidelines/
├── shared/                              # TRULY shared (all roles)
│   ├── INDEX.md                         # Updated index
│   ├── CONTEXT7.md                      # Keep, remove duplicates elsewhere
│   ├── TDD.md                           # SLIM DOWN - principles only
│   ├── QUALITY.md                       # Keep, consolidate duplicates
│   ├── VALIDATION_OVERVIEW.md           # NEW - high-level only
│   ├── STATE_MACHINE_OVERVIEW.md        # NEW - task/QA states
│   ├── PRINCIPLES.md                    # NEW - core Edison principles
│   ├── HONEST_STATUS.md                 # Keep
│   ├── GIT_WORKFLOW.md                  # Keep
│   ├── REFACTORING.md                   # Keep
│   └── EPHEMERAL_SUMMARIES_POLICY.md    # Keep
│
├── developer/                           # NEW - shared by agents+validators
│   ├── INDEX.md                         # Index for developer guidelines
│   ├── NO_MOCKS_POLICY.md               # NEW - extracted
│   ├── TYPE_SAFETY_PRINCIPLES.md        # NEW - extracted
│   ├── ERROR_HANDLING.md                # NEW - extracted
│   ├── CONFIGURATION_FIRST.md           # NEW - extracted
│   ├── TEST_ISOLATION.md                # NEW - extracted
│   ├── ACCESSIBILITY.md                 # NEW - extracted
│   └── CODE_PATTERNS.md                 # NEW - generic patterns
│
├── agents/                              # AGENT-ONLY
│   ├── COMMON.md                        # UPDATE - reference developer/
│   ├── MANDATORY_WORKFLOW.md            # Keep
│   ├── OUTPUT_FORMAT.md                 # Keep
│   ├── TDD_EXECUTION.md                 # NEW - moved from TDD.md
│   ├── CONTEXT7_REQUIREMENT.md          # SLIM - reference shared/CONTEXT7.md
│   ├── DELEGATION_AWARENESS.md          # Keep
│   ├── VALIDATION_AWARENESS.md          # SLIM - reference shared/VALIDATION_OVERVIEW.md
│   ├── IMPORTANT_RULES.md               # Keep
│   ├── AGENT_WORKFLOW.md                # Keep
│   └── EDISON_CLI.md                    # Keep
│
├── validators/                          # VALIDATOR-ONLY
│   ├── VALIDATOR_COMMON.md              # UPDATE - reference developer/
│   ├── VALIDATOR_WORKFLOW.md            # Keep
│   ├── VALIDATOR_GUIDELINES.md          # Keep
│   ├── OUTPUT_FORMAT.md                 # Keep
│   ├── TDD_COMPLIANCE_CHECK.md          # NEW - how to check TDD
│   ├── VALIDATION_EXECUTION.md          # NEW - moved from VALIDATION.md
│   └── EDISON_CLI.md                    # Keep
│
└── orchestrators/                       # ORCHESTRATOR-ONLY
    ├── ORCHESTRATOR_GUIDELINES.md       # Keep
    ├── DELEGATION.md                    # Keep
    ├── SESSION_WORKFLOW.md              # Keep
    ├── VALIDATOR_ORCHESTRATION.md       # NEW - moved from VALIDATION.md
    ├── TDD_VERIFICATION.md              # NEW - moved from TDD.md
    ├── STATE_MACHINE_GUARDS.md          # Keep
    └── EDISON_CLI.md                    # Keep
```

---

## PART F: PACK UPDATES

### F1. Python Pack Changes

**REMOVE from `packs/python/guidelines/python/TESTING.md`:**

- Generic NO MOCKS philosophy (reference `developer/NO_MOCKS_POLICY.md`)
- Generic TDD workflow (reference `shared/TDD.md`)
- Generic test isolation (reference `developer/TEST_ISOLATION.md`)

**KEEP in `packs/python/guidelines/python/TESTING.md`:**

- pytest-specific syntax and fixtures
- tmp_path usage patterns
- Python-specific real database testing (SQLite)
- pytest markers and parametrize
- Python async testing patterns

**REMOVE from `packs/python/guidelines/python/TYPING.md`:**

- Generic type safety principles (reference `developer/TYPE_SAFETY_PRINCIPLES.md`)

**KEEP:**

- mypy configuration
- Python-specific syntax (list[T], T | None)
- Protocol, TypeVar, ParamSpec patterns
- Python-specific type ignore handling

**REMOVE from `packs/python/guidelines/python/PYTHON.md`:**

- Generic error handling (reference `developer/ERROR_HANDLING.md`)
- Generic configuration principles (reference `developer/CONFIGURATION_FIRST.md`)

**KEEP:**

- pathlib.Path usage
- Dataclasses, Enum, match statements
- Python module structure
- ruff/mypy tool usage

### F2. Vitest Pack Changes

**REMOVE from `packs/vitest/validators/testing.md`:**

- Generic TDD compliance (reference `validators/TDD_COMPLIANCE_CHECK.md`)
- Generic NO MOCKS (reference `developer/NO_MOCKS_POLICY.md`)
- Generic test isolation (reference `developer/TEST_ISOLATION.md`)

**KEEP:**

- Vitest-specific patterns
- React Testing Library patterns
- Playwright patterns
- vi.mock/vi.spyOn usage

### F3. React Pack Changes

**REMOVE from `packs/react/validators/react.md`:**

- Generic accessibility (reference `developer/ACCESSIBILITY.md`)
- Generic type safety (reference `developer/TYPE_SAFETY_PRINCIPLES.md`)

**KEEP:**

- React 19 patterns (use(), Server Components)
- Hooks rules
- Component patterns
- React-specific accessibility (ARIA in JSX)

### F4. All Other Packs

Apply same pattern:

- Remove generic content → reference developer/ guidelines
- Keep technology-specific syntax and patterns

---

## PART G: AGENT FILE UPDATES

### G1. feature-implementer.md

**REMOVE:**

- Generic TDD protocol (~30 lines) → reference `agents/TDD_EXECUTION.md`
- Generic delegation awareness → reference `agents/DELEGATION_AWARENESS.md`
- Generic validation awareness → reference `agents/VALIDATION_AWARENESS.md`
- Context7 examples (~30 lines) → reference `shared/CONTEXT7.md`

**KEEP:**

- Role description
- Scope definition
- Feature-specific workflow
- Output format reference

### G2. test-engineer.md

**REMOVE:**

- Generic TDD (~50 lines) → reference `agents/TDD_EXECUTION.md`
- Generic NO MOCKS → reference `developer/NO_MOCKS_POLICY.md`
- Generic test isolation → reference `developer/TEST_ISOLATION.md`
- Context7 examples → reference `shared/CONTEXT7.md`

**KEEP:**

- Role description
- Test-specific workflow
- Testing patterns section reference

### G3. code-reviewer.md

**REMOVE:**

- Context7 examples → reference `shared/CONTEXT7.md`
- Generic validation awareness → reference `validators/VALIDATOR_COMMON.md`

**KEEP:**

- Role description (review-only)
- Review checklist
- Why code review cannot be delegated

### G4. python-developer.md

**REMOVE:**

- Generic TDD for Python → reference `agents/TDD_EXECUTION.md`
- Generic type hints → reference `developer/TYPE_SAFETY_PRINCIPLES.md`
- Generic NO MOCKS → reference `developer/NO_MOCKS_POLICY.md`

**KEEP:**

- Python-specific tools (mypy, ruff, pytest commands)
- Python-specific patterns
- Python file structure

---

## PART H: CONSTITUTION UPDATES

### H1. AGENTS.md Constitution

**Update Mandatory Preloads:**

```markdown
## Mandatory Preloads (All Agents)
- shared/PRINCIPLES.md: Core Edison principles
- shared/CONTEXT7.md: Context7 usage (single source)
- shared/TDD.md: TDD principles (not execution details)
- developer/INDEX.md: Developer guidelines index
- agents/COMMON.md: Agent baseline
- agents/MANDATORY_WORKFLOW.md: Claim-Implement-Ready
- agents/TDD_EXECUTION.md: How to execute TDD
- agents/OUTPUT_FORMAT.md: Report format
```

**DO NOT LOAD:**

- orchestrators/* (not relevant to agents)
- validators/* (agents don't validate)
- shared/VALIDATION.md full content (only awareness)

### H2. VALIDATORS.md Constitution

**Update Mandatory Preloads:**

```markdown
## Mandatory Preloads (All Validators)
- shared/PRINCIPLES.md: Core Edison principles
- shared/CONTEXT7.md: Context7 usage
- shared/VALIDATION_OVERVIEW.md: High-level validation
- developer/INDEX.md: Developer guidelines (for code review)
- validators/VALIDATOR_COMMON.md: Validator baseline
- validators/VALIDATOR_WORKFLOW.md: Validation workflow
- validators/TDD_COMPLIANCE_CHECK.md: How to check TDD
- validators/OUTPUT_FORMAT.md: Report format
```

**DO NOT LOAD:**

- orchestrators/* (not relevant to validators)
- agents/MANDATORY_WORKFLOW.md (validators don't implement)
- agents/TDD_EXECUTION.md (validators don't execute TDD)

### H3. ORCHESTRATORS.md Constitution

**Update Mandatory Preloads:**

```markdown
## Mandatory Preloads (All Orchestrators)
- shared/PRINCIPLES.md: Core Edison principles
- shared/CONTEXT7.md: Context7 usage
- shared/TDD.md: TDD principles
- orchestrators/SESSION_WORKFLOW.md: Session management
- orchestrators/DELEGATION.md: Delegation decisions
- orchestrators/VALIDATOR_ORCHESTRATION.md: How to orchestrate validators
- orchestrators/TDD_VERIFICATION.md: How to verify TDD compliance
```

**DO NOT LOAD:**

- agents/TDD_EXECUTION.md (orchestrator doesn't execute TDD)
- agents/MANDATORY_WORKFLOW.md (orchestrator delegates, not implements)
- validators/VALIDATOR_WORKFLOW.md (orchestrator orchestrates, not validates)
- developer/* (orchestrator verifies, doesn't implement)

---

## PART I: REFERENCE PATTERNS

### I1. How to Reference Guidelines

**IN AGENT FILES:**

```markdown
## TDD Requirements (MANDATORY)
See `guidelines/agents/TDD_EXECUTION.md` for complete workflow.
See `guidelines/developer/NO_MOCKS_POLICY.md` for testing philosophy.
```

**IN VALIDATOR FILES:**

```markdown
## TDD Compliance Check
See `guidelines/validators/TDD_COMPLIANCE_CHECK.md` for verification steps.
See `guidelines/developer/NO_MOCKS_POLICY.md` for what to flag.
```

**IN PACK FILES:**

```markdown
## Testing Guidelines
See `guidelines/developer/NO_MOCKS_POLICY.md` for core philosophy.
See `guidelines/developer/TEST_ISOLATION.md` for isolation patterns.

### Python-Specific Testing
[Keep only Python-specific content here]
```

---

## PART J: ESTIMATED LINE COUNT CHANGES

| File | Current | After | Change |

|------|---------|-------|--------|

| shared/TDD.md | ~297 | ~100 | -197 |

| shared/VALIDATION.md | ~181 | ~50 | -131 |

| shared/QUALITY.md | ~248 | ~200 | -48 |

| packs/python/TESTING.md | ~583 | ~200 | -383 |

| packs/vitest/testing.md | ~760 | ~300 | -460 |

| agents/feature-implementer.md | ~370 | ~200 | -170 |

| agents/test-engineer.md | ~503 | ~250 | -253 |

| **NEW developer/* files** | 0 | ~500 | +500 |

| **NEW orchestrator files** | 0 | ~300 | +300 |

| **NEW validator files** | 0 | ~100 | +100 |

**Net reduction per role context:**

- Orchestrator: -300 lines (doesn't load agent/validator execution details)
- Agent: -200 lines (doesn't load orchestrator/validator details)
- Validator: -200 lines (doesn't load orchestrator/agent execution details)

---

## PART K: MIGRATION ORDER

### Phase 1: Create New Infrastructure

1. Create `guidelines/developer/` directory
2. Create INDEX.md files for each subdirectory
3. Create `guidelines/shared/PRINCIPLES.md`

### Phase 2: Extract Developer Guidelines

4. Create `developer/NO_MOCKS_POLICY.md`
5. Create `developer/TYPE_SAFETY_PRINCIPLES.md`
6. Create `developer/ERROR_HANDLING.md`
7. Create `developer/CONFIGURATION_FIRST.md`
8. Create `developer/TEST_ISOLATION.md`
9. Create `developer/ACCESSIBILITY.md`

### Phase 3: Split Shared Files

10. Split `shared/TDD.md` → keep principles, move execution/verification
11. Split `shared/VALIDATION.md` → keep overview, move orchestration/execution
12. Create `shared/VALIDATION_OVERVIEW.md`
13. Create `orchestrators/VALIDATOR_ORCHESTRATION.md`
14. Create `orchestrators/TDD_VERIFICATION.md`
15. Create `validators/TDD_COMPLIANCE_CHECK.md`
16. Create `validators/VALIDATION_EXECUTION.md`
17. Create `agents/TDD_EXECUTION.md`

### Phase 4: Update Packs

18. Update Python pack (remove generic, add references)
19. Update Vitest pack (remove generic, add references)
20. Update React pack (remove generic, add references)
21. Update remaining packs (Prisma, NextJS, Tailwind, TypeScript)

### Phase 5: Update Agent/Validator Files

22. Update feature-implementer.md (slim down, add references)
23. Update test-engineer.md (slim down, add references)
24. Update code-reviewer.md (slim down, add references)
25. Update python-developer.md (slim down, add references)
26. Update all validator files (slim down, add references)

### Phase 6: Update Constitutions

27. Update AGENTS.md constitution (mandatory preloads)
28. Update VALIDATORS.md constitution (mandatory preloads)
29. Update ORCHESTRATORS.md constitution (mandatory preloads)

### Phase 7: Validation

30. Run `edison compose --all` to regenerate
31. Verify no broken references
32. Verify context sizes reduced for each role
33. Test with actual agent/validator/orchestrator runs

### To-dos

- [ ] Create guidelines/developer/NO_MOCKS_POLICY.md with extracted content
- [ ] Create guidelines/developer/ERROR_HANDLING.md with extracted content
- [ ] Create guidelines/developer/TYPE_SAFETY.md with extracted content
- [ ] Create guidelines/developer/CONFIGURATION_FIRST.md with extracted content
- [ ] Create guidelines/developer/TEST_ISOLATION.md with extracted content
- [ ] Create guidelines/developer/ACCESSIBILITY.md with extracted content
- [ ] Consolidate TDD content into shared/TDD.md
- [ ] Update Python pack to reference developer guidelines
- [ ] Update Vitest pack to reference developer guidelines
- [ ] Update validators to reference developer guidelines