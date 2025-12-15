# Edison Prompt Engineering Rules

This file defines the mandatory rules for developing/modifying agents, validators, orchestrators, constitutions, and guidelines in Edison.

## Core Principles (All Roles)

### Single Source of Truth
- Every rule/guideline exists in ONE canonical file
- All other files include from that source via `<!-- ERROR: File not found for section extract: }}`
- Change in one place propagates everywhere -->`.

## File Organization

```
guidelines/
├── includes/          # NEVER read directly (section-only)
│   └── {TOPIC}.md    # Has role-specific sections
├── agents/           # Agent-readable
├── validators/       # Validator-readable
├── orchestrators/    # Orchestrator-readable
└── shared/           # Optional deep-dives

agents/               # Constitution embedded
validators/           # Constitution embedded
constitutions/        # Include-only (embedded in prompts)
packs/{pack}/         # Technology-specific extensions
```

## Templating Rules

### Includes
```markdown
## TDD Execution (Agents)

### Mandatory Workflow

#### 1. RED Phase: Write Tests First
Write tests BEFORE any implementation code. Tests MUST fail initially.

**Verify RED Phase**:
```bash
<run test command from active test framework>
# Expected: Test FAILS (implementation not written yet)
```

**RED Phase Checklist**:
- [ ] Test written BEFORE implementation
- [ ] Test fails when run
- [ ] Test failure message is clear
- [ ] Test covers the specific functionality

#### 2. GREEN Phase: Minimal Implementation
Write the MINIMUM code needed to make the test pass.

**Verify GREEN Phase**:
```bash
<run test command from active test framework>
# Expected: Test PASSES
```

**GREEN Phase Checklist**:
- [ ] Implementation makes test pass
- [ ] No extra code beyond what's needed
- [ ] Test passes consistently

#### 3. REFACTOR Phase: Clean Up
Improve code quality while keeping tests passing.

**Verify REFACTOR Phase**:
```bash
<run test command from active test framework>
# Expected: ALL tests still PASS
```

**REFACTOR Phase Checklist**:
- [ ] Code is cleaner/more readable
- [ ] Error handling added
- [ ] Validation added
- [ ] ALL tests still pass

### Evidence Requirements
- Test file created/committed BEFORE implementation file (verify via git history)
- Commits MUST include explicit markers: `[RED]` then `[GREEN]` (in order)
- RED failure documented → GREEN pass documented → REFACTOR documented
- Attach test output showing the failing run and the passing run
- Include a coverage report for the round
- Store evidence in the task round evidence directory using the **config-driven filenames** (e.g. `command-test.txt`, `coverage-*.txt` when configured)
- If TDD must be skipped, record the rationale in the implementation report + QA brief and create a follow-up task to add the missing tests; do not silently skip

### What NOT To Do
**NEVER**:
- Implement before writing tests
- "I'll add tests later" - NO!
- Skip test verification (RED phase must fail)
- Use excessive mocking (test real behavior)
- Leave skipped/focused/disabled tests in committed code
- Commit with failing tests

### Performance Targets
| Test Type | Target Time | Description |
|-----------|-------------|-------------|
| Unit tests | <100ms each | Pure logic, no external dependencies |
| Integration tests | <1s each | Multiple components working together |
| API/Service tests | <100ms each | Service layer with real dependencies |
| UI/Component tests | <200ms each | Rendering and interaction tests |
| End-to-End tests | <5s each | Full user journey tests |
```
- Use section includes, not full file includes
- Resolution: project → packs → core

### Sections
```markdown
<!-- SECTION: name -->
Content
<!-- /SECTION: name -->
```
- Required for all content that varies by role
- Required for pack extension points

### Pack Extensions
```markdown

Pack-specific content

```
- Packs ONLY use EXTEND (never redefine sections)
- No generic content in pack extensions

## Agent Development Rules

### Agent Template
```markdown
---
name: {agent-name}
---

<!-- ERROR: Include not found: constitutions/agents-base.md -->

## Role
[Agent-specific role description]

## Tools
<!-- SECTION: tools -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tools -->

## Guidelines
<!-- SECTION: guidelines -->
<!-- /SECTION: guidelines -->

## Workflow
[Agent-specific workflow]
```

### Agent Rules
1. Constitution embedded first
2. No generic TDD/NO_MOCKS (in constitution)
3. No technology content (in pack overlays)
4. SECTION placeholders for tools/guidelines
5. Only role-specific content remains

## Validator Development Rules

### Validator Template
```markdown
<!-- ERROR: Include not found: constitutions/validators-base.md -->

## Mission
[What this validates]

## Triggers
`**/*.test.*`

## Checklist
<!-- SECTION: checklist -->
[Generic checks]
<!-- /SECTION: checklist -->

## Tech Checks
<!-- SECTION: tech-checks -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tech-checks -->
```

### Validator Rules
1. Constitution embedded first
2. Clear triggers and blocking status
3. Generic checklist in core
4. SECTION: tech-checks for packs

## Pack Development Rules

### Pack Overlay Pattern
```markdown
---
name: {target-agent}
pack: {pack}
overlay_type: extend
---

### {Pack} Tools
{Technology-specific commands}

<!-- ERROR: File not found for section extract: packs/{pack}/guidelines/TESTING.md -->

```

### Pack Rules
1. EXTEND only (never redefine)
2. No generic content (TDD philosophy, etc.)
3. Only technology-specific content
4. Include from pack guidelines for complex patterns

## Guidelines Development Rules

### Includes File Structure
```markdown
<!-- SECTION: principles -->
## {Topic} Principles (All Roles)
[Universal principles]
<!-- /SECTION: principles -->

<!-- SECTION: agent-{action} -->
## {Topic} for Agents
[Agent-specific]
<!-- /SECTION: agent-{action} -->

<!-- SECTION: validator-{action} -->
## {Topic} for Validators
[Validator-specific]
<!-- /SECTION: validator-{action} -->

<!-- SECTION: orchestrator-{action} -->
## {Topic} for Orchestrators
[Orchestrator-specific]
<!-- /SECTION: orchestrator-{action} -->
```

### Guidelines Rules
1. Includes files have ALL role sections
2. Shared files are truly shared (all roles benefit)
3. No duplicated content across files
4. Sections properly marked with comments

## Anti-Patterns (FORBIDDEN)

### Double-Loading
```markdown
# FORBIDDEN
mandatoryReads: [shared/TDD.md]
<!-- ERROR: Include not found: shared/TDD.md -->  # <-- Same content twice!
```

### Technology in Core
```markdown
# FORBIDDEN in core agent
- pytest tests/   # <-- Python-specific!
- pnpm test       # <-- Node-specific!
```

### Hardcoded Dynamic Content
```markdown
# FORBIDDEN
Valid states: todo, wip, done

# CORRECT
Valid states: {{fn:task_states}}
```

### Generic Content in Packs
```markdown
# FORBIDDEN in pack
## TDD Principles      # <-- Generic, belongs in core!
```

### Copying Instead of Including
```markdown
# FORBIDDEN
[50 lines copied from another file]

# CORRECT
<!-- ERROR: File not found for section extract: path -->
```

### Wrong-Role Content
```markdown
# FORBIDDEN in agent
## Validator Wave Orchestration  # <-- Orchestrator-only!
```

## Quality Checklist

Before any prompt change:
- [ ] Content is technology-agnostic (core) or technology-specific (pack)?
- [ ] Content already exists in canonical source?
- [ ] Including correct role-specific section?
- [ ] No double-loading?
- [ ] SECTION markers present for extension?

After changes:
- [ ] `edison compose --all` succeeds
- [ ] No broken includes/sections
- [ ] No duplicate content in composed output
- [ ] Each role loads only their content