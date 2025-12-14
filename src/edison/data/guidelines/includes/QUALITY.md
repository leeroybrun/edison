# Quality Standards - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: principles -->
## Quality Principles (All Roles)

### Type Safety
- No untyped escape hatches
- Justify any type suppressions (language-specific ignore directives, dynamic-typing escape hatches)
- Type safety settings come from project configuration

### Code Hygiene
- No TODO/FIXME placeholders in production code
- No stray console.log or debug statements
- Remove dead code
- No commented-out code blocks

### Error Handling
- Async flows expose clear `loading` / `error` / `empty` states
- Errors are properly caught and handled
- User-facing errors are meaningful

### DRY & SOLID
- No code duplication—extract to shared utilities
- Single Responsibility Principle
- Open/Closed Principle
- Liskov Substitution Principle
- Interface Segregation Principle
- Dependency Inversion Principle

### Configuration-First
- No hardcoded values—all config from YAML
- No magic numbers or strings in code
- Every behavior must be configurable
<!-- /section: principles -->

<!-- section: agent-checklist -->
## Quality Checklist (Agents)

### Before Marking Ready
- [ ] **Type checking passes** - No type errors
- [ ] **Linting passes** - No lint warnings
- [ ] **No TODOs** - No TODO/FIXME in production code
- [ ] **Error handling complete** - All errors properly handled
- [ ] **Input validation present** - User inputs validated
- [ ] **Tests passing** - All tests green
- [ ] **No debug code** - No console.log, print statements
- [ ] **No hardcoded values** - Config from YAML
- [ ] **No code duplication** - DRY principle followed

### Artifact Completeness
- Task document is self-contained: assumptions, scope boundaries, interfaces/contracts, explicit acceptance criteria
- QA brief is self-contained: preconditions, explicit commands, expected results
- Evidence paths are recorded in the task/QA docs

### Verification Commands
Before marking any task as ready, run:
```bash
# Verify all automation passes
<type-check-command> && <lint-command> && <test-command> && <build-command>
```
All must pass with zero warnings.
<!-- /section: agent-checklist -->

<!-- section: validator-checklist -->
## Quality Validation (Validators)

### Type Safety Check
- [ ] No type-system escape hatches without justification
- [ ] No ignore directives without an explicit rationale
- [ ] Project type-safety settings are enforced

### Code Smell Check
- [ ] No god classes (excessive responsibilities)
- [ ] No feature envy (manipulating other class's data)
- [ ] No inappropriate intimacy (reaching into internals)
- [ ] Functions under 30 lines
- [ ] No deep nesting (max 3 levels)
- [ ] No hidden side effects

### Naming Check
- [ ] Names are clear about purpose
- [ ] No abbreviations without context
- [ ] Consistent naming across modules
- [ ] Boolean names are positive

### Duplication Check
- [ ] No copy-pasted logic
- [ ] No reimplemented standard library functions
- [ ] Repeated validation centralized
- [ ] Single source of truth for constants

### Architecture Check
- [ ] No tight coupling between modules
- [ ] No circular dependencies
- [ ] No global mutable state
- [ ] No layer violations
<!-- /section: validator-checklist -->
