<!-- 3586ed4c-83d4-402b-b34c-42118219eed2 c8396b52-8a1a-4a5a-8edf-d806c3fc4c7d -->
# Complete Edison Guidelines Unification Plan

## Executive Summary

This plan addresses six critical issues:

1. **Duplicated content** across 75+ files → Single canonical source files in `includes/`
2. **Double-loading** (constitution + prompt duplication) → Constitution EMBEDDED in agent/validator prompts
3. **Wrong-role content** (orchestrator content loaded by agents) → Role-specific sections in includes
4. **Technology in core** (Python/Vitest patterns in core agents) → Packs use EXTEND only
5. **Hardcoded dynamic content** → Template functions (`{{fn:...}}`)
6. **Complex re-read instructions** → Single file per role to re-read on compact

---

## PART A: ARCHITECTURAL DECISIONS

### A1. Constitution Embedding (KEY CHANGE)

**Problem**: Current system has constitution + agent prompt as separate files. Agents must remember to re-read constitution on compact.

**Solution**: Constitution is EMBEDDED in agent/validator prompt via `{{include:}}`.

```markdown
# agents/test-engineer.md

{{include:constitutions/agents-base.md}}

## Test Engineer Role
[Agent-specific content]
```

**Benefits**:

- "Re-read your agent file on compact" = gets EVERYTHING
- No risk of forgetting constitution
- Single source of truth
- Automatic propagation of constitution changes

### A2. Includes Folder Pattern

Files in `guidelines/includes/` exist ONLY for `{{include-section:...}}`. They are NEVER read directly.

### A3. Technology-Agnostic Core

Core agents/validators have ZERO technology content. Packs inject via `<!-- EXTEND: section -->`.

### A4. No Pack Conditionals in Core

NO `{{if:has-pack(python)}}` in core files. Packs EXTEND sections instead.

---

## PART B: DUPLICATION ANALYSIS (Current State)

### B1. Files with TDD Content: 75 files

- `shared/TDD.md` (297 lines)
- `agents/TDD_REQUIREMENT.md` (363 lines) - OVERLAPS with shared
- Every agent file (30-50 lines each)
- Every validator file
- Pack guidelines

### B2. Files with NO MOCKS Content: 23 files

- `shared/QUALITY.md`
- `python/TESTING.md`
- `vitest/testing.md`
- Every agent file
- Every validator file

### B3. Files with Context7 Content: 52 files

- `shared/CONTEXT7.md` (57 lines)
- `agents/CONTEXT7_REQUIREMENT.md` (221 lines) - OVERLAPS
- Every agent file (30+ lines each)
- Every validator file

### B4. Constitution/Prompt Duplication

| Content | Constitution mandatoryReads | Agent Prompt | Result |

|---------|---------------------------|--------------|--------|

| TDD | YES | YES (embedded) | DOUBLE |

| Context7 | YES | YES (embedded) | DOUBLE |

| QUALITY | YES | YES (referenced) | DOUBLE |

---

## PART C: NEW FILE STRUCTURE

```
guidelines/
├── includes/                    # NEVER READ DIRECTLY (section-only)
│   ├── TDD.md                  # sections: principles, agent-execution, validator-check, orchestrator-verify
│   ├── NO_MOCKS.md             # sections: philosophy, agent-impl, validator-flags
│   ├── CONTEXT7.md             # sections: workflow, agent-markers, validator-check
│   ├── QUALITY.md              # sections: principles, agent-checklist, validator-checklist
│   ├── HONEST_STATUS.md        # sections: agent-rules, orchestrator-verify
│   ├── TYPE_SAFETY.md          # sections: principles, agent-impl, validator-check
│   ├── ERROR_HANDLING.md       # sections: principles, agent-impl, validator-check
│   ├── TEST_ISOLATION.md       # sections: principles, agent-impl, validator-check
│   ├── CONFIGURATION.md        # sections: principles, check
│   └── VALIDATION.md           # sections: overview, orchestrator-waves, validator-workflow
│
├── agents/                      # Agent-readable (minimal - workflow only)
│   ├── MANDATORY_WORKFLOW.md   # Claim-Implement-Ready (with workflow section)
│   └── OUTPUT_FORMAT.md        # Report format
│
├── validators/                  # Validator-readable (minimal)
│   ├── VALIDATOR_WORKFLOW.md   # Intake-Verdict (with workflow section)
│   └── OUTPUT_FORMAT.md        # Report format
│
├── orchestrators/               # Orchestrator-readable (minimal)
│   ├── SESSION_WORKFLOW.md     # Session management (with workflow section)
│   └── DELEGATION.md           # Delegation rules (with rules section)
│
└── shared/                      # Deep-dive optional references ONLY
    ├── QUALITY_PATTERNS.md     # Extended examples (optional read)
    ├── GIT_WORKFLOW.md         # Git conventions (optional read)
    └── REFACTORING.md          # Refactoring patterns (optional read)

constitutions/                   # INCLUDE-ONLY (embedded in agents/validators)
├── agents-base.md              # Embedded at top of every agent
├── validators-base.md          # Embedded at top of every validator
└── orchestrator-base.md        # Embedded at top of orchestrator prompts

agents/                          # Final composed prompts
├── test-engineer.md            # {{include:constitutions/agents-base.md}} + role-specific
├── feature-implementer.md
├── component-builder.md
├── api-builder.md
├── database-architect.md
└── code-reviewer.md

validators/
├── global/global.md            # {{include:constitutions/validators-base.md}} + validator-specific
├── critical/*.md
└── ...
```

---

## PART D: INCLUDES FILE DESIGNS

### D1. `includes/TDD.md` (~350 lines total, each role loads ~80)

```markdown
<!-- SECTION: principles -->
## TDD Principles (All Roles)
- RED: Write failing test first
- GREEN: Minimal implementation to pass
- REFACTOR: Clean with tests green
- No .skip/.todo committed
- Coverage targets from config
- Commits tagged [RED] then [GREEN]
<!-- /SECTION: principles -->

<!-- SECTION: agent-execution -->
## TDD Execution (Agents)
- Test file BEFORE implementation (verify via git history)
- Commit tags: [RED] → [GREEN] → [REFACTOR]
- Evidence files: red-phase.txt, green-phase.txt
- Coverage reports required
- Use `edison task ready --run` to capture trusted evidence
[Full execution patterns...]
<!-- /SECTION: agent-execution -->

<!-- SECTION: validator-check -->
## TDD Compliance (Validators)
- Verify git history shows test-first
- Check for [RED]/[GREEN] commits
- Flag tests written after implementation
- Flag .skip/.only in committed tests
- Flag mocks of internal modules
<!-- /SECTION: validator-check -->

<!-- SECTION: orchestrator-verify -->
## TDD Verification (Orchestrators)
- Verification checklist before accepting work
- Red flags to watch for
- Delegation templates requiring TDD
[Full delegation templates from current TDD.md...]
<!-- /SECTION: orchestrator-verify -->
```

### D2. `includes/NO_MOCKS.md` (~120 lines)

```markdown
<!-- SECTION: philosophy -->
## NO MOCKS Philosophy (All Roles)
- Test real behavior, not mocked behavior
- Only mock external APIs at system boundaries
- Real databases, real auth, real files
- Mocking internal code = testing nothing
<!-- /SECTION: philosophy -->

<!-- SECTION: agent-implementation -->
## NO MOCKS Implementation (Agents)
- Use tmp_path for file tests
- Use real SQLite/template DBs
- Use TestClient for API tests
- Fixtures use real resources
[Python-specific: pytest patterns]
[Vitest-specific: RTL patterns]
<!-- /SECTION: agent-implementation -->

<!-- SECTION: validator-flags -->
## NO MOCKS Validation (Validators)
- Flag unittest.mock imports
- Flag @patch decorators
- Flag vi.mock of internal modules (prisma, auth)
- Flag mocked databases
<!-- /SECTION: validator-flags -->
```

### D3. `includes/CONTEXT7.md` (~100 lines)

```markdown
<!-- SECTION: workflow -->
## Context7 Workflow (All Roles)
1. Resolve library ID: `mcp__context7__resolve_library_id`
2. Query docs: `mcp__context7__get_library_docs`
3. Implement/validate using current docs, not training memory
<!-- /SECTION: workflow -->

<!-- SECTION: agent-markers -->
## Context7 Evidence (Agents)
- Create `context7-<pkg>.txt` per package
- Include topics queried and doc version/date
- HMAC stamp when enabled in config
- Guards block `wip→done` without markers
- Notes in task files NOT accepted as evidence
<!-- /SECTION: agent-markers -->

<!-- SECTION: validator-check -->
## Context7 Validation (Validators)
- Refresh knowledge BEFORE validating
- Query for packages in active packs
- Verify marker files exist for post-training packages
- Check patterns match current docs
<!-- /SECTION: validator-check -->
```

### D4. `includes/QUALITY.md` (~150 lines)

```markdown
<!-- SECTION: principles -->
## Quality Principles (All Roles)
- Type safety (no any without justification)
- DRY (no code duplication)
- SOLID principles
- No magic numbers
- No hardcoded credentials
<!-- /SECTION: principles -->

<!-- SECTION: agent-checklist -->
## Quality Checklist (Agents)
- Type checking passes
- Linting passes
- No TODOs in production code
- Error handling complete
- Input validation present
<!-- /SECTION: agent-checklist -->

<!-- SECTION: validator-checklist -->
## Quality Validation (Validators)
- Check type coverage
- Check for code smells
- Check security basics
- Check performance patterns
<!-- /SECTION: validator-checklist -->
```

### D5. `includes/HONEST_STATUS.md` (~60 lines)

```markdown
<!-- SECTION: agent-rules -->
## Honest Status (Agents)
- NEVER mark complete with TODOs
- NEVER mark complete with failing tests
- NEVER mark complete with skipped tests
- Report EXACT state, not hopeful state
- Use `blocked` status when blocked
<!-- /SECTION: agent-rules -->

<!-- SECTION: orchestrator-verify -->
## Status Verification (Orchestrators)
- Verify status matches reality
- Check for hidden blockers
- Verify evidence exists
<!-- /SECTION: orchestrator-verify -->
```

### D6. `includes/VALIDATION.md` (~200 lines)

```markdown
<!-- SECTION: overview -->
## Validation Overview (All Roles)
- Global → Critical → Specialized waves
- Verdicts: approve, reject, blocked
- Bundle-first rule
<!-- /SECTION: overview -->

<!-- SECTION: orchestrator-waves -->
## Validator Orchestration (Orchestrators)
[Full wave execution content from current VALIDATION.md]
[Concurrency management]
[Bundle approval process]
[Parent/child validation]
<!-- /SECTION: orchestrator-waves -->

<!-- SECTION: validator-workflow -->
## Validation Execution (Validators)
- How to load bundle
- How to write reports
- Follow-up creation rules
<!-- /SECTION: validator-workflow -->
```

---

## PART E: CONSTITUTION DESIGNS

### E1. Agent Constitution (`constitutions/agents-base.md`)

```markdown
# Agent Constitution

**Re-read this file (your agent prompt) on every compact and task start.**

## Role Definition
You are an AGENT (implementer) in Edison. You implement code changes following TDD.

## Core Principles (CRITICAL)
{{include-section:guidelines/includes/TDD.md#principles}}
{{include-section:guidelines/includes/NO_MOCKS.md#philosophy}}
{{include-section:guidelines/includes/QUALITY.md#principles}}

## TDD Execution (MANDATORY)
{{include-section:guidelines/includes/TDD.md#agent-execution}}

## NO MOCKS Implementation
{{include-section:guidelines/includes/NO_MOCKS.md#agent-implementation}}

## Context7 Knowledge Refresh
{{include-section:guidelines/includes/CONTEXT7.md#workflow}}
{{include-section:guidelines/includes/CONTEXT7.md#agent-markers}}

## Honest Status
{{include-section:guidelines/includes/HONEST_STATUS.md#agent-rules}}

## Mandatory Workflow
{{include-section:guidelines/agents/MANDATORY_WORKFLOW.md#workflow}}

## Quality Checklist
{{include-section:guidelines/includes/QUALITY.md#agent-checklist}}

## Output Format
See: `guidelines/agents/OUTPUT_FORMAT.md`

## Optional Deep-Dive References
- `guidelines/shared/QUALITY_PATTERNS.md` - Extended examples
- `guidelines/shared/GIT_WORKFLOW.md` - Git conventions
```

### E2. Validator Constitution (`constitutions/validators-base.md`)

```markdown
# Validator Constitution

**Re-read this file (your validator prompt) on every compact and validation start.**

## Role Definition
You are a VALIDATOR in Edison. You review code for production-readiness.

## Core Principles (CRITICAL)
{{include-section:guidelines/includes/TDD.md#principles}}
{{include-section:guidelines/includes/NO_MOCKS.md#philosophy}}
{{include-section:guidelines/includes/QUALITY.md#principles}}

## TDD Compliance Checking
{{include-section:guidelines/includes/TDD.md#validator-check}}

## NO MOCKS Validation
{{include-section:guidelines/includes/NO_MOCKS.md#validator-flags}}

## Context7 Validation
{{include-section:guidelines/includes/CONTEXT7.md#workflow}}
{{include-section:guidelines/includes/CONTEXT7.md#validator-check}}

## Validation Workflow
{{include-section:guidelines/includes/VALIDATION.md#overview}}
{{include-section:guidelines/validators/VALIDATOR_WORKFLOW.md#workflow}}

## Quality Validation
{{include-section:guidelines/includes/QUALITY.md#validator-checklist}}

## Output Format
See: `guidelines/validators/OUTPUT_FORMAT.md`
```

### E3. Orchestrator Constitution (`constitutions/orchestrator-base.md`)

```markdown
# Orchestrator Constitution

**Re-read this file on every compact and session start.**

## Role Definition
You are an ORCHESTRATOR in Edison. You manage sessions, delegate tasks, orchestrate validation.

## Core Principles (CRITICAL)
{{include-section:guidelines/includes/TDD.md#principles}}
{{include-section:guidelines/includes/HONEST_STATUS.md#orchestrator-verify}}

## TDD Verification
{{include-section:guidelines/includes/TDD.md#orchestrator-verify}}

## Validation Orchestration
{{include-section:guidelines/includes/VALIDATION.md#overview}}
{{include-section:guidelines/includes/VALIDATION.md#orchestrator-waves}}

## Session Workflow
{{include-section:guidelines/orchestrators/SESSION_WORKFLOW.md#workflow}}

## Delegation Rules
{{include-section:guidelines/orchestrators/DELEGATION.md#rules}}
```

---

## PART F: AGENT PROMPT DESIGN

### F1. Agent Template

```markdown
---
name: test-engineer
description: "TDD guardian ensuring test quality"
model: codex
---

# Test Engineer

## Constitution (Re-read on compact)
{{include:constitutions/agents-base.md}}

## Role
- Design automated tests (unit, integration, e2e)
- Ensure TDD compliance (tests lead implementation)
- Verify coverage and test quality

## Tools
<!-- SECTION: tools -->
<!-- Base tools - pack overlays extend here -->
<!-- /SECTION: tools -->

## Guidelines
<!-- SECTION: guidelines -->
<!-- Base guidelines - pack overlays extend here -->
<!-- /SECTION: guidelines -->

## Test Engineer Workflow
1. Receive test task from orchestrator
2. Write failing tests FIRST (RED)
3. Verify tests fail for right reason
4. (Wait for/provide implementation GREEN)
5. Verify all tests pass
6. Return complete results

## Constraints
- TEST FIRST, ALWAYS
- VERIFY FAILURE before implementation
- FAST TESTS (<100ms unit)
- QUALITY > COVERAGE
```

**Note**: NO TDD explanation (in constitution). NO technology patterns (in pack overlays).

### F2. Pack Overlay Pattern

**`packs/python/agents/overlays/test-engineer.md`:**

````markdown
---
name: test-engineer
pack: python
overlay_type: extend
---

<!-- EXTEND: tools -->
### Python Testing (pytest)
```bash
pytest tests/ -v --tb=short
pytest tests/ --cov=src --cov-report=term-missing
mypy tests/
````

<!-- /EXTEND -->

<!-- EXTEND: guidelines -->

### Python Testing Patterns

{{include-section:packs/python/guidelines/python/TESTING.md#pytest-patterns}}

{{include-section:packs/python/guidelines/python/TESTING.md#fixtures}}

<!-- /EXTEND -->

````

**`packs/vitest/agents/overlays/test-engineer.md`:**

```markdown
<!-- EXTEND: tools -->
### Vitest Testing
```bash
pnpm test
pnpm test -- --coverage
````

<!-- /EXTEND -->

<!-- EXTEND: guidelines -->

### Vitest Patterns

{{include-section:packs/vitest/guidelines/vitest/TESTING.md#vitest-patterns}}

<!-- /EXTEND -->

````

---

## PART G: VALIDATOR PROMPT DESIGN

### G1. Validator Template

```markdown
# Global Validator

## Constitution (Re-read on compact)
{{include:constitutions/validators-base.md}}

## Mission
Comprehensive code review for production-readiness.

## 10-Point Checklist
<!-- SECTION: checklist -->
1. Task completion
2. Code quality
3. Security
4. Performance
5. Error handling
6. TDD compliance
7. Architecture
8. Best practices
9. Regression testing
10. Documentation
<!-- /SECTION: checklist -->

## Tech Stack
<!-- SECTION: tech-stack -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tech-stack -->
````

### G2. Pack Validator Overlays

```markdown
# packs/python/validators/overlays/global.md

<!-- EXTEND: tech-stack -->
### Python Validation
- mypy --strict must pass
- ruff check must pass
- No unittest.mock imports
- pytest fixtures use real resources
<!-- /EXTEND -->
```

---

## PART H: FUNCTIONS FOR DYNAMIC CONTENT

### H1. State Machine Functions

**`functions/state_machine.py`:**

```python
def task_states() -> str:
    """Return task states from state-machine.yaml."""
    # Load from config, not hardcoded
    
def qa_states() -> str:
    """Return QA states from config."""

def state_transitions(domain: str = "task") -> str:
    """Return valid transitions as markdown table."""

def state_diagram(domain: str = "task") -> str:
    """Return mermaid diagram."""
```

### H2. Update Existing Function

**`functions/tasks_states.py`:**

```python
# UPDATE: Read from state-machine.yaml instead of hardcoded TASK_STATES list
def tasks_states(state: Optional[str] = None) -> str:
    config = load_config("state-machine.yaml")
    states = config["task"]["states"]
    # ...
```

---

## PART I: FILES TO DELETE

After migration, delete:

| File | Reason |

|------|--------|

| `guidelines/agents/TDD_REQUIREMENT.md` | Content in `includes/TDD.md`, embedded in constitution |

| `guidelines/agents/CONTEXT7_REQUIREMENT.md` | Content in `includes/CONTEXT7.md`, embedded in constitution |

| `guidelines/shared/SHARED_COMMON.md` | Content moved to constitution |

| `guidelines/shared/TDD.md` | Replaced by `includes/TDD.md` |

| `guidelines/shared/CONTEXT7.md` | Replaced by `includes/CONTEXT7.md` |

| `guidelines/shared/QUALITY.md` | Split: principles → `includes/QUALITY.md`, examples → `shared/QUALITY_PATTERNS.md` |

| `guidelines/shared/HONEST_STATUS.md` | Replaced by `includes/HONEST_STATUS.md` |

| `guidelines/shared/VALIDATION.md` | Replaced by `includes/VALIDATION.md` |

| `guidelines/agents/VALIDATION_AWARENESS.md` | Overview now in constitution |

---

## PART J: PACK GUIDELINES CHANGES

### J1. Remove from Pack Guidelines:

- Generic TDD explanation (now in constitution)
- Generic NO MOCKS philosophy (now in constitution)
- Generic test isolation (now in includes)
- Generic type safety (now in includes)

### J2. Keep in Pack Guidelines:

- Technology-specific commands
- Technology-specific patterns
- SECTION markers for overlay references

### J3. Example Pack Guideline

**`packs/python/guidelines/python/TESTING.md`:**

```markdown
# Python Testing Guide

## Pytest Configuration
<!-- SECTION: pytest-config -->
[Python-specific pyproject.toml]
<!-- /SECTION: pytest-config -->

## Fixtures
<!-- SECTION: fixtures -->
[Python-specific fixture patterns]
<!-- /SECTION: fixtures -->

## Pytest Patterns
<!-- SECTION: pytest-patterns -->
[parametrize, markers, async]
<!-- /SECTION: pytest-patterns -->
```

---

## PART K: CONSTITUTION.YAML CHANGES

**OLD:**

```yaml
agents:
  mandatoryReads:
    - path: shared/TDD.md
    - path: shared/CONTEXT7.md
    - path: agents/MANDATORY_WORKFLOW.md
    # ... many files
```

**NEW:**

```yaml
agents:
  mandatoryReads: []  # EMPTY - all critical content embedded in agent prompts
  optionalReads:
    - path: guidelines/shared/QUALITY_PATTERNS.md
      purpose: Extended examples (on-demand)
    - path: guidelines/shared/GIT_WORKFLOW.md
      purpose: Git conventions (on-demand)

validators:
  mandatoryReads: []  # EMPTY - all critical content embedded
  optionalReads:
    - path: guidelines/shared/QUALITY_PATTERNS.md

orchestrator:
  mandatoryReads: []  # EMPTY - all critical content embedded
  optionalReads:
    - path: AVAILABLE_AGENTS.md
    - path: AVAILABLE_VALIDATORS.md
```

---

## PART L: MIGRATION PHASES

### Phase 1: Create Includes Infrastructure (Day 1)

1. Create `guidelines/includes/` directory
2. Create `includes/TDD.md` with all role sections
3. Create `includes/NO_MOCKS.md` with all role sections
4. Create `includes/CONTEXT7.md` with all role sections
5. Create `includes/QUALITY.md` with all role sections
6. Create `includes/HONEST_STATUS.md` with all role sections
7. Create `includes/VALIDATION.md` with all role sections
8. Create `includes/TYPE_SAFETY.md`
9. Create `includes/ERROR_HANDLING.md`
10. Create `includes/TEST_ISOLATION.md`
11. Create `includes/CONFIGURATION.md`

### Phase 2: Redesign Constitutions (Day 2)

12. Update `agents-base.md` - embed via include-section
13. Update `validators-base.md` - embed via include-section
14. Update `orchestrator-base.md` - embed via include-section

### Phase 3: Redesign Agent Prompts (Day 3)

15. Update `test-engineer.md` - add `{{include:constitution}}`, slim content
16. Update `feature-implementer.md` - same pattern
17. Update `component-builder.md`
18. Update `api-builder.md`
19. Update `database-architect.md`
20. Update `code-reviewer.md`

### Phase 4: Redesign Validator Prompts (Day 4)

21. Update `global.md` - add `{{include:constitution}}`, slim content
22. Update all critical validators
23. Update all specialized validators

### Phase 5: Update Pack Overlays (Day 5)

24. Update Python pack overlays (use EXTEND only)
25. Update Vitest pack overlays
26. Update React pack overlays
27. Update NextJS pack overlays
28. Update remaining pack overlays

### Phase 6: Slim Pack Guidelines (Day 6)

29. Remove generic content from Python pack guidelines
30. Remove generic content from Vitest pack guidelines
31. Remove generic content from all pack guidelines
32. Add SECTION markers for overlay references

### Phase 7: Create Functions (Day 7)

33. Create `functions/state_machine.py`
34. Update `functions/tasks_states.py` to read from config

### Phase 8: Cleanup (Day 8)

35. Delete redundant files (see Part I)
36. Update `constitution.yaml` - empty mandatoryReads
37. Move `shared/QUALITY.md` → `shared/QUALITY_PATTERNS.md`

### Phase 9: Validate (Day 9)

38. Run `edison compose --all`
39. Verify no broken includes/sections
40. Verify context sizes reduced
41. Test with real agent/validator/orchestrator runs
42. Verify NO duplication in composed outputs
43. Verify re-read instructions work

---

## PART M: SUCCESS METRICS

| Metric | Before | After |

|--------|--------|-------|

| Files with TDD content | 75 | 1 (`includes/TDD.md`) |

| Files with NO MOCKS content | 23 | 1 (`includes/NO_MOCKS.md`) |

| Files with Context7 content | 52 | 1 (`includes/CONTEXT7.md`) |

| Agent prompt size | ~500 lines | ~150 lines + constitution |

| Constitution/prompt duplication | YES | NO |

| Technology in core agents | YES | NO |

| Files to update for TDD change | 75 | 1 |

| Re-read instructions | 2 files | 1 file |

| mandatoryReads in constitution.yaml | Many | 0 |

---

## PART N: KEY PRINCIPLES SUMMARY

1. **Constitution Embedding**: Constitution is INCLUDED in agent/validator prompts, not separate
2. **Includes Folder**: Files in `includes/` are NEVER read directly - only via `{{include-section:}}`
3. **Single Re-Read**: "Re-read your agent file" = gets constitution + role content
4. **Technology-Agnostic Core**: Core has ZERO technology content - packs EXTEND
5. **No Double-Loading**: Content in exactly ONE place per role
6. **Single Source of Truth**: Change includes file → propagates to all
7. **Functions for Dynamic**: State machine from config, not hardcoded
8. **Empty mandatoryReads**: All critical content embedded, optionalReads for deep-dives

### To-dos

- [ ] Create includes/ directory with TDD.md, NO_MOCKS.md, CONTEXT7.md, QUALITY.md, HONEST_STATUS.md, VALIDATION.md (all with role sections)
- [ ] Redesign constitutions to embed critical content via include-section
- [ ] Redesign all 6 agent prompts: add {{include:constitution}}, slim to role-specific content
- [ ] Redesign all validator prompts: add {{include:constitution}}, slim content
- [ ] Update all pack overlays to use EXTEND pattern only (Python, Vitest, React, NextJS, etc.)
- [ ] Remove generic content from pack guidelines, add SECTION markers
- [ ] Create state_machine.py, update tasks_states.py to read from config
- [ ] Delete redundant files, update constitution.yaml to empty mandatoryReads
- [ ] Run edison compose --all, verify sizes reduced, test re-read instructions