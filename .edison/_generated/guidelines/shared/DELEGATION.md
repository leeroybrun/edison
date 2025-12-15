# Delegation Patterns (Shared)

> For orchestrators delegating work and agents receiving delegated work.

## Delegation Principles

### When to Delegate
- **Multi-skill work**: Task spans multiple domains (backend + frontend + data)
- **Time-sensitive**: Parallelizable independent work within concurrency cap
- **Specialized expertise**: Security, performance, database, UX requiring focused skill
- **Non-trivial scope**: Task requires >30 minutes or multiple files
- **Scale**: Large refactors or features splittable into independent slices

### When NOT to Delegate
- **Trivial edits**: Single-line fixes, typos, obvious renames (faster to do than brief)
- **Config prohibits**: Task flagged `neverImplementDirectly: false` or similar
- **Already focused**: You are the assigned specialist for this exact work
- **Coordination overhead**: Briefing cost exceeds implementation cost

### Why Delegate
- **Leverage specialization**: Right expert for the right task
- **Maximize throughput**: Parallel execution within concurrency limits
- **Maintain quality**: Focused agents produce better results
- **Preserve independence**: Separate implementers from validators

## Clear Task Definition

### Task Brief Must Include

#### 1. Core Context
- **Task ID**: Unique identifier for tracking
- **Task Type**: Feature, bug fix, refactor, test, documentation
- **Priority**: Critical, high, normal, low
- **Scope Boundaries**: What's IN scope and OUT of scope

#### 2. Requirements
- **Acceptance Criteria**: Explicit, testable conditions for completion
- **Constraints**: TDD required, no mocks, no hardcoded values, no legacy code
- **Dependencies**: Blocking tasks, required data, external systems
- **File Scope**: Specific files/directories to modify or create

#### 3. Technical Guidance
- **Patterns**: Which existing patterns to follow (provide file references)
- **Integration Points**: APIs, databases, external services to integrate
- **Configuration**: YAML files to read/update, no hardcoded values
- **Error Handling**: Expected error scenarios and handling strategy

#### 4. Deliverables
- **Code Changes**: Specific files expected
- **Tests**: Test files and coverage requirements (≥90%)
- **Evidence**: Commands to run and expected outputs
- **Documentation**: Implementation report location and format

### Task Brief Template

```markdown
# Task: <brief-title>

**ID**: <task-id>
**Type**: feature|bugfix|refactor|test|docs
**Priority**: critical|high|normal|low
**Assigned To**: <agent-role>
**Estimated Effort**: <time-estimate>

## Scope

**In Scope:**
- <specific-item-1>
- <specific-item-2>

**Out of Scope:**
- <explicitly-excluded-item-1>
- <explicitly-excluded-item-2>

## Requirements

### Acceptance Criteria
1. <testable-criterion-1>
2. <testable-criterion-2>
3. <testable-criterion-3>

### Constraints
- TDD required (RED → GREEN → REFACTOR)
- No mocks
- No hardcoded values (read from YAML)

## Technical Notes
- <existing patterns to follow>
- <files to reference>

## Deliverables
- Code changes in <file scope>
- Tests added/updated
- Evidence files recorded
- Implementation report JSON
```