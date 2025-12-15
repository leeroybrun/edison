# Edison Guidelines Index

> Quick reference for all Edison guidelines. Use this to find the right guide for your task.

## Core Principles (MANDATORY for all roles)

### Critical Principles
- **Path**: `guidelines/edison/CRITICAL_PRINCIPLES.md`
- **Purpose**: 16 non-negotiable principles for Edison development
- **When to Read**: Before any Edison development work
- **Key Topics**: TDD, NO MOCKS, NO HARDCODING, DRY, ROOT CAUSE, REFACTORING ESSENTIALS

### TDD (Test-Driven Development)
- **Canonical**: Embedded in role constitutions (`constitutions/AGENTS.md`, `constitutions/VALIDATORS.md`, `constitutions/ORCHESTRATOR.md`)
- **Purpose**: RED→GREEN→REFACTOR workflow
- **When to Read**: Before implementing any feature
- **Key Topics**: Test-first development, coverage targets (≥90% overall, 100% on new files), no mocks

### Context7 Requirements
- **Path**: `guidelines/shared/CONTEXT7.md`
- **Purpose**: Post-training package documentation lookup
- **When to Read**: Before using any library/framework
- **Key Topics**: MCP tool usage, evidence markers, resolve-then-query workflow

### Validation Workflow
- **Path**: `guidelines/shared/VALIDATION.md`
- **Purpose**: How validation system works
- **When to Read**: Before marking work ready for validation
- **Key Topics**: Validator tiers (Global/Critical/Specialized), wave execution, bundle rules

## Role-Specific Guidelines

### For Agents
- **`guidelines/agents/COMMON.md`** - Shared agent workflow, Context7 usage, TDD requirements
- **`guidelines/agents/MANDATORY_WORKFLOW.md`** - Claim-Implement-Ready cycle, implementation steps
- **`guidelines/agents/OUTPUT_FORMAT.md`** - Implementation report JSON format
- **`guidelines/agents/VALIDATION_AWARENESS.md`** - Why validation matters, how to pass first try
- **`guidelines/agents/DELEGATION_AWARENESS.md`** - Delegation rules, MISMATCH pattern, never re-delegate
- **`guidelines/agents/AGENT_WORKFLOW.md`** - Detailed agent workflow steps
- **`guidelines/agents/EDISON_CLI.md`** - Edison CLI commands for agents

### For Validators
- **`guidelines/validators/VALIDATOR_COMMON.md`** - Shared validator rules
- **`guidelines/validators/VALIDATOR_WORKFLOW.md`** - Intake→Execute→Verdict→Report→Handoff workflow
- **`guidelines/validators/OUTPUT_FORMAT.md`** - Validator report JSON format
- **`guidelines/validators/EDISON_CLI.md`** - Edison CLI commands for validators

### For Orchestrators
- **`guidelines/orchestrators/SESSION_WORKFLOW.md`** - Session management, worktree isolation, state transitions
- **`guidelines/orchestrators/DELEGATION.md`** - Configuration-driven delegation rules
- **`guidelines/orchestrators/STATE_MACHINE_GUARDS.md`** - State transition guards
- **`guidelines/orchestrators/EDISON_CLI.md`** - Edison CLI commands for orchestrators

## Python-Specific Guidelines

### Type Hints
- **Path**: `guidelines/python/TYPING.md`
- **Purpose**: Strict type checker compliance
- **When to Read**: Before writing Python code
- **Key Topics**: Type annotations, generics, forward references, type checker configuration

### Testing
- **Path**: `guidelines/python/TESTING.md`
- **Purpose**: Test framework patterns without mocks
- **When to Read**: Before writing tests
- **Key Topics**: NO MOCKS policy, fixtures, tmp_path, real behavior testing

### Async
- **Path**: `guidelines/python/ASYNC.md`
- **Purpose**: asyncio patterns
- **When to Read**: When implementing async code
- **Key Topics**: async/await, event loops, concurrent operations, error handling

### Python Overview
- **Path**: `guidelines/python/PYTHON.md`
- **Purpose**: General Python best practices for Edison
- **When to Read**: Before starting Python development
- **Key Topics**: Project structure, imports, code style, tooling (type checker, linter, test runner)

## Additional Shared Guidelines

### Quality Standards
- **Path**: `guidelines/shared/QUALITY.md`
- **Purpose**: Code quality expectations
- **When to Read**: During implementation
- **Key Topics**: Coverage targets, code review standards, documentation

### Git Workflow
- **Path**: `guidelines/shared/GIT_WORKFLOW.md`
- **Purpose**: Git practices and patterns
- **When to Read**: Before committing code
- **Key Topics**: Commit messages, branching, PR workflow, worktree usage

### Delegation
- **Path**: `guidelines/shared/DELEGATION.md`
- **Purpose**: Shared delegation patterns
- **When to Read**: When delegating work to sub-agents
- **Key Topics**: Task decomposition, delegation boundaries, orchestrator patterns

### Honest Status
- **Path**: `guidelines/shared/HONEST_STATUS.md`
- **Purpose**: Accurate status reporting
- **When to Read**: When reporting task status
- **Key Topics**: Status integrity, blocked vs failed, escalation patterns

### Refactoring
- **Path**: `guidelines/shared/REFACTORING.md`
- **Purpose**: Refactoring principles and patterns
- **When to Read**: Before starting refactoring work
- **Key Topics**: Update ALL callers, no legacy code, maintaining tests green

### Ephemeral Summaries Policy
- **Path**: `guidelines/shared/EPHEMERAL_SUMMARIES_POLICY.md`
- **Purpose**: Prohibition of summary files
- **When to Read**: Before creating any documentation
- **Key Topics**: No NOTES.md, no SUMMARY.md, canonical evidence only

### Pack-Specific Patterns
- **Path**: `packs/<pack>/guidelines/**` (composed into `.edison/_generated/guidelines/**` when active)
- **Purpose**: Technology-specific patterns provided by active packs
- **When to Read**: When implementing features covered by an active pack
- **Key Topics**: Pack-specific best practices, constraints, and checklists

## Usage Pattern

Reference guidelines selectively in prompts:

```markdown
## Mandatory Reading
- Re-read your role constitution for TDD workflow
- See `guidelines/python/TYPING.md` for type hint requirements
- See `guidelines/agents/MANDATORY_WORKFLOW.md` for implementation steps
```

## How to Add New Guidelines

1. Create file in appropriate subdirectory (`shared/`, `agents/`, `python/`, etc.)
2. Add entry to this INDEX.md
3. Include: Path, Purpose, When to Read, Key Topics
4. Update relevant constitution files to reference the new guideline if mandatory

## Guidelines Directory Structure

```
guidelines/
├── shared/          # Cross-cutting guidelines for all roles
├── agents/          # Agent-specific guidelines
├── validators/      # Validator-specific guidelines
├── orchestrators/   # Orchestrator-specific guidelines
└── python/          # Python pack guidelines (in packs/python/)
```

Note: Python guidelines are stored in `src/edison/data/packs/python/guidelines/python/` and composed into `.edison/_generated/guidelines/python/` during build.