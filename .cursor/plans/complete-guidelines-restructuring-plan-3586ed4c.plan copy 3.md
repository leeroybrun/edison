<!-- 3586ed4c-83d4-402b-b34c-42118219eed2 60a35e6c-0a7c-412c-a5e8-32a8e5d549e2 -->
# Unified Guidelines Restructuring Plan

## Core Principles

### P1: Includes Folder Pattern

Files that exist ONLY to be included via `{{include-section:...}}` live in `guidelines/includes/`. This prevents LLMs from loading the complete file directly.

**Structure:**

```
guidelines/
├── includes/               # NEVER READ DIRECTLY - section-only files
│   ├── TDD.md             # Has sections for each role
│   ├── NO_MOCKS.md        # Has sections for each role
│   ├── TYPE_SAFETY.md
│   ├── ERROR_HANDLING.md
│   ├── TEST_ISOLATION.md
│   └── CONFIGURATION.md
├── agents/                 # AGENT-ONLY files (can be read)
├── validators/             # VALIDATOR-ONLY files (can be read)
├── orchestrators/          # ORCHESTRATOR-ONLY files (can be read)
└── shared/                 # Files truly shared (CONTEXT7.md, etc)
```

### P2: Technology-Agnostic Core

Core agents/validators contain ZERO technology-specific content. Packs use `<!-- EXTEND: section -->` to inject their specifics.

**Example - Core `test-engineer.md`:**

```markdown
## Tools
<!-- SECTION: tools -->
<!-- Base tools here -->
<!-- /SECTION: tools -->
```

**Example - Pack `python/agents/overlays/test-engineer.md`:**

```markdown
<!-- EXTEND: tools -->
### Python Testing (pytest)
- pytest commands here
<!-- /EXTEND -->
```

### P3: Constitution vs Agent Prompt Separation

Content appears in EXACTLY ONE place:

| Content Type | Location | Rationale |

|--------------|----------|-----------|

| Universal critical rules (TDD principles, NO MOCKS philosophy) | **Constitution ONLY** | All agents/validators read constitution first |

| Role-specific workflow (Claim-Implement-Ready) | **Constitution ONLY** | Applies to all agents equally |

| Agent-type-specific patterns | **Agent prompt ONLY** | test-engineer specifics, component-builder specifics |

| Technology-specific patterns | **Pack overlays ONLY** | Python pytest, Vitest patterns |

---

## Part A: Includes File Design

### A1. `guidelines/includes/TDD.md`

```markdown
<!-- SECTION: principles -->
## TDD Principles (All Roles)
- RED: Write failing test first
- GREEN: Minimal implementation to pass
- REFACTOR: Clean up with tests green
- No .skip/.todo committed
<!-- /SECTION: principles -->

<!-- SECTION: agent-execution -->
## TDD Execution (Agents Only)
- Create test file BEFORE implementation
- Commit [RED] then [GREEN] tags
- Evidence file creation patterns
<!-- /SECTION: agent-execution -->

<!-- SECTION: validator-check -->
## TDD Compliance Checks (Validators Only)
- Verify git history shows test-first
- Check for [RED]/[GREEN] commit tags
- Flag tests written after implementation
<!-- /SECTION: validator-check -->

<!-- SECTION: orchestrator-verify -->
## TDD Verification (Orchestrators Only)
- Verification checklist before accepting work
- Red flags to watch for
- Delegation templates requiring TDD
<!-- /SECTION: orchestrator-verify -->
```

### A2. `guidelines/includes/NO_MOCKS.md`

```markdown
<!-- SECTION: philosophy -->
## NO MOCKS Philosophy (All Roles)
- Test real behavior, not mocked behavior
- Only mock external APIs at system boundaries
- Real databases, real auth, real files
<!-- /SECTION: philosophy -->

<!-- SECTION: agent-implementation -->
## NO MOCKS Implementation (Agents Only)
- Use tmp_path for file tests
- Use real SQLite/template DBs
- Use TestClient for API tests
<!-- /SECTION: agent-implementation -->

<!-- SECTION: validator-flags -->
## NO MOCKS Validation (Validators Only)
- Flag unittest.mock imports
- Flag @patch decorators
- Flag vi.mock of internal modules
<!-- /SECTION: validator-flags -->
```

### A3. Other includes files

- `TYPE_SAFETY.md` - principles + agent patterns + validator checks
- `ERROR_HANDLING.md` - principles + patterns + validation
- `TEST_ISOLATION.md` - principles + patterns + checks
- `CONFIGURATION.md` - no hardcoding rules

---

## Part B: Constitution Redesign

### B1. Agent Constitution (`constitutions/agents-base.md`)

**Include critical content directly via include-section:**

```markdown
# Agent Constitution

## Core Principles (Embedded)
{{include-section:guidelines/includes/TDD.md#principles}}
{{include-section:guidelines/includes/NO_MOCKS.md#philosophy}}

## Mandatory Workflow
{{include-section:guidelines/agents/MANDATORY_WORKFLOW.md#workflow}}

## TDD Execution Requirements
{{include-section:guidelines/includes/TDD.md#agent-execution}}

## Context7 Knowledge Refresh
{{include-section:guidelines/shared/CONTEXT7.md#workflow}}

## Output Requirements
See: `guidelines/agents/OUTPUT_FORMAT.md`

## Deep-Dive References (On-Demand)
- `guidelines/shared/QUALITY.md` - Extended patterns
- `guidelines/shared/GIT_WORKFLOW.md` - Git conventions
```

**Critically: Agent prompt files DO NOT re-include these sections.**

### B2. Validator Constitution (`constitutions/validators-base.md`)

```markdown
# Validator Constitution

## Core Principles (Embedded)
{{include-section:guidelines/includes/TDD.md#principles}}
{{include-section:guidelines/includes/NO_MOCKS.md#philosophy}}

## TDD Compliance Checking
{{include-section:guidelines/includes/TDD.md#validator-check}}

## NO MOCKS Validation
{{include-section:guidelines/includes/NO_MOCKS.md#validator-flags}}

## Validation Workflow
{{include-section:guidelines/validators/VALIDATOR_WORKFLOW.md#workflow}}

## Output Requirements
See: `guidelines/validators/OUTPUT_FORMAT.md`
```

### B3. Orchestrator Constitution (`constitutions/orchestrator-base.md`)

```markdown
# Orchestrator Constitution

## Core Principles (Embedded)
{{include-section:guidelines/includes/TDD.md#principles}}

## TDD Verification
{{include-section:guidelines/includes/TDD.md#orchestrator-verify}}

## Session Workflow
{{include-section:guidelines/orchestrators/SESSION_WORKFLOW.md#workflow}}

## Delegation Rules
{{include-section:guidelines/orchestrators/DELEGATION.md#rules}}

## Validator Orchestration
{{include-section:guidelines/orchestrators/VALIDATOR_ORCHESTRATION.md#waves}}
```

---

## Part C: Agent Prompt Redesign

### C1. Core Agent Pattern (Technology-Agnostic)

**`agents/test-engineer.md`** - NO technology-specific content:

```markdown
---
name: test-engineer
description: "TDD guardian ensuring test quality"
---

## Constitution Awareness
**Role**: AGENT | **Constitution**: AGENTS.md
Re-read constitution at task start. Constitution > Guidelines > Task.

## Role
- Design automated tests (unit, integration, e2e)
- Ensure TDD compliance (tests lead implementation)
- Verify coverage and test quality

## Tools
<!-- SECTION: tools -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tools -->

## Guidelines
<!-- SECTION: guidelines -->
<!-- Pack overlays extend here -->
<!-- /SECTION: guidelines -->

## Workflow
1. Receive task from orchestrator
2. Check delegation config
3. Write failing tests FIRST (RED)
4. Verify tests fail for right reason
5. Implement minimal code (GREEN)
6. Refactor with tests green
7. Return complete results

## Output Format
See: `guidelines/agents/OUTPUT_FORMAT.md`
```

**Note:** NO TDD explanation here - it's in the constitution. NO technology patterns - they come from pack overlays.

### C2. Pack Overlay Pattern

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
pnpm test -- --watch
````

<!-- /EXTEND -->

<!-- EXTEND: guidelines -->

### Vitest Patterns

{{include-section:packs/vitest/guidelines/vitest/TESTING.md#vitest-patterns}}

{{include-section:packs/vitest/guidelines/vitest/TESTING.md#rtl-patterns}}

<!-- /EXTEND -->

````

---

## Part D: Validator Prompt Redesign

### D1. Core Validator Pattern

**`validators/testing.md`** - Technology-agnostic:

```markdown
# Testing Validator
**Scope**: TDD compliance, test quality, coverage
**Triggers**: `**/*.test.*`, `**/*.spec.*`
**Blocks**: YES

## Mission
Validate test quality and TDD compliance.

## Checklist
<!-- SECTION: checklist -->
- [ ] Tests written BEFORE implementation (git history)
- [ ] RED/GREEN commit tags present
- [ ] Coverage meets threshold
- [ ] No .skip/.only committed
- [ ] Tests use real behavior (not mocks)
<!-- /SECTION: checklist -->

## Tech Stack Checks
<!-- SECTION: tech-checks -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tech-checks -->
````

### D2. Pack Validator Overlays

**`packs/python/validators/overlays/testing.md`:**

```markdown
<!-- EXTEND: tech-checks -->
### Python Testing Checks
- mypy --strict must pass
- No unittest.mock imports
- No @patch decorators
- pytest fixtures use real resources
<!-- /EXTEND -->
```

**`packs/vitest/validators/overlays/testing.md`:**

```markdown
<!-- EXTEND: tech-checks -->
### Vitest Testing Checks
- vi.mock only for external APIs
- No vi.mock of internal modules (prisma, auth)
- React Testing Library queries by role/text
<!-- /EXTEND -->
```

---

## Part E: Shared Guidelines Restructuring

### E1. Files to KEEP in `shared/`

These are truly shared and can be read directly:

- `CONTEXT7.md` - Context7 workflow (all roles need)
- `QUALITY.md` - Code quality patterns (deep-dive reference)
- `GIT_WORKFLOW.md` - Git conventions
- `HONEST_STATUS.md` - Status reporting rules
- `REFACTORING.md` - Refactoring patterns

### E2. Files to MOVE to `includes/`

Move and split by role sections:

- `TDD.md` → `includes/TDD.md` (with role sections)
- `VALIDATION.md` → Split:
  - Orchestrator parts → `includes/VALIDATION.md#orchestrator-waves`
  - Validator parts → `includes/VALIDATION.md#validator-workflow`
  - Overview → Keep minimal in `shared/VALIDATION_OVERVIEW.md`

### E3. Files to DELETE

Remove after content is moved to includes:

- `shared/TDD.md` (replaced by `includes/TDD.md`)
- `shared/SHARED_COMMON.md` (content moved to constitution includes)
- `agents/TDD_REQUIREMENT.md` (now in constitution)
- `agents/CONTEXT7_REQUIREMENT.md` (now in constitution)

---

## Part F: Pack Guidelines Restructuring

### F1. Pattern for Pack Guidelines

Pack guideline files should:

1. Include generic principles from `includes/` (if not already in constitution)
2. Keep ONLY technology-specific patterns
3. Define sections that pack overlays can reference

**Example - `packs/python/guidelines/python/TESTING.md`:**

```markdown
# Python Testing Guide

## Pytest Configuration
<!-- SECTION: pytest-config -->
[Python-specific pyproject.toml patterns]
<!-- /SECTION: pytest-config -->

## Fixtures
<!-- SECTION: fixtures -->
[Python-specific fixture patterns]
<!-- /SECTION: fixtures -->

## Pytest Patterns
<!-- SECTION: pytest-patterns -->
[parametrize, markers, async testing]
<!-- /SECTION: pytest-patterns -->
```

**What to REMOVE from pack guidelines:**

- Generic TDD explanation (in constitution)
- Generic NO MOCKS philosophy (in constitution)
- Generic test isolation principles (in includes)

---

## Part G: Functions for Dynamic Content

### G1. State Machine Functions

**Create `functions/state_machine.py`:**

```python
def task_states() -> str:
    """Return task states from config as markdown list."""
    # Load from state-machine.yaml, not hardcoded
    
def qa_states() -> str:
    """Return QA states from config as markdown list."""

def state_transitions(domain: str = "task") -> str:
    """Return valid transitions as markdown table."""
```

### G2. Update `tasks_states.py`

Read from config instead of hardcoded list.

---

## Part H: Content Allocation Summary

### Constitution Content (CRITICAL - Embedded)

- TDD principles and agent execution requirements
- NO MOCKS philosophy and implementation rules
- Mandatory workflow (Claim-Implement-Ready)
- Context7 workflow
- Output format references

### Agent/Validator Prompt Content (ROLE-SPECIFIC)

- Role description and expertise
- Section placeholders for pack overlays
- Workflow steps specific to that agent type
- Guide references table

### Pack Overlay Content (TECHNOLOGY-SPECIFIC)

- Tool commands (pytest, vitest, mypy, etc.)
- Technology-specific patterns
- Technology-specific validation checks

### Includes Content (NEVER READ DIRECTLY)

- Full TDD documentation with role sections
- Full NO MOCKS documentation with role sections
- Full validation documentation with role sections

---

## Part I: Migration Phases

### Phase 1: Create Infrastructure

1. Create `guidelines/includes/` directory
2. Create state_machine.py functions
3. Update tasks_states.py to read from config

### Phase 2: Create Includes Files

4. Create `includes/TDD.md` with all role sections
5. Create `includes/NO_MOCKS.md` with all role sections
6. Create `includes/TYPE_SAFETY.md` with role sections
7. Create `includes/TEST_ISOLATION.md`
8. Create `includes/ERROR_HANDLING.md`
9. Create `includes/CONFIGURATION.md`

### Phase 3: Redesign Constitutions

10. Update `agents-base.md` - embed via include-section
11. Update `validators-base.md` - embed via include-section
12. Update `orchestrator-base.md` - embed via include-section
13. Update `constitution.yaml` - remove mandatory reads that are now embedded

### Phase 4: Slim Core Agents

14. Remove all generic content from `test-engineer.md`
15. Remove all generic content from `feature-implementer.md`
16. Remove all generic content from other core agents
17. Ensure all have proper SECTION placeholders for packs

### Phase 5: Slim Core Validators

18. Remove generic content from `testing.md`
19. Remove generic content from `global.md`
20. Ensure proper SECTION placeholders for packs

### Phase 6: Update Pack Overlays

21. Update Python pack overlays to use EXTEND only
22. Update Vitest pack overlays to use EXTEND only
23. Update React pack overlays
24. Update remaining pack overlays

### Phase 7: Update Pack Guidelines

25. Remove generic content from pack guidelines
26. Add proper SECTION markers for overlay references
27. Keep only technology-specific patterns

### Phase 8: Cleanup Shared Guidelines

28. Delete `shared/TDD.md` (now in includes)
29. Delete `shared/SHARED_COMMON.md` (now in constitution)
30. Delete agent-specific requirement files (now in constitution)
31. Slim `shared/VALIDATION.md` to overview only

### Phase 9: Validate

32. Run `edison compose --all`
33. Verify no broken includes/sections
34. Verify context sizes reduced
35. Test with real agent/validator/orchestrator runs
36. Verify NO duplication in composed outputs

---

## Success Metrics

| Metric | Before | Target |

|--------|--------|--------|

| Duplicated lines in source | ~2000 | 0 |

| Agent context size | ~1500 lines | ~600 lines |

| Validator context size | ~1200 lines | ~500 lines |

| Files to update for TDD rule change | ~15 | 1 |

| Double-loaded content | Present | Zero |

| Pack-conditional in core | Present | Zero |

| Constitution/prompt duplication | Present | Zero |

### To-dos

- [ ] Create guidelines/includes/ directory and state_machine.py functions
- [ ] Create includes/TDD.md, NO_MOCKS.md, TYPE_SAFETY.md with role sections
- [ ] Redesign constitutions to embed critical content via include-section
- [ ] Remove generic content from core agents, add SECTION placeholders
- [ ] Remove generic content from core validators, add SECTION placeholders
- [ ] Update all pack overlays to use EXTEND pattern only
- [ ] Slim pack guidelines to technology-specific content with SECTION markers
- [ ] Delete redundant shared files (TDD.md, SHARED_COMMON.md, etc.)
- [ ] Run edison compose --all, verify sizes reduced, test with real tasks