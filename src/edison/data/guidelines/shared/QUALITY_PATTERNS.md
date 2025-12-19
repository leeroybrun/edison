# Quality Standards (Core)


## Quality Checklist
- **Type Safety:** No untyped escape hatches; justify any suppressions.
- **Error Surfaces:** Async flows expose clear `loading` / `error` / `empty` states.
- **UX & Accessibility:** Responsive across breakpoints; keyboard + screen-reader friendly; no contrast violations.
- **Code Hygiene:** No TODO/FIXME placeholders; no stray logs; remove dead code.
- **Testing:** Prefer real behavior over mocks on critical paths; deterministic, isolated tests with no `.only`/`.skip`/`.todo`.
- **Performance & Parallel Safety:** Avoid shared global state; use unique identifiers for data created in tests or fixtures.

## Code Smell Checklist

### Naming Smells
- Names are unclear or ambiguous about purpose or scope.
- Abbreviations or acronyms are used without being obvious domain terms.
- Names encode types or data structures (e.g., `user_list_dict`).
- Boolean names use negatives or double negatives (`not_enabled`, `isNotReady`).
- Same concept named differently across modules (e.g., `user_id` vs `uid`).
- Inconsistent tense/pluralization between interfaces and implementations.
- Function or variable names include ticket numbers or transient context.

### Function Smells
- Functions exceed a single, clear responsibility.
- Functions are long (e.g., > 30 lines) with hard-to-scan control flow.
- Functions accept too many parameters (more than 4) instead of grouping meaningfully.
- Flag parameters toggle multiple behaviors instead of splitting into dedicated functions.
- Deep nesting (more than 3 levels) obscures the happy path.
- Hidden side effects (mutating external state, performing I/O unexpectedly).
- Mixed levels of abstraction inside the same function (low-level details next to orchestration).

### Class Smells
- God classes accumulating unrelated concerns.
- Feature envy: a class frequently manipulating another class’s data directly.
- Data clumps moved around together instead of encapsulated.
- Inappropriate intimacy: reaching into another class’s internals instead of using its API.
- Classes with excessive public surface area not justified by consumers.
- Classes exposing setters for invariants that should be established at construction.
- Subclasses overriding only parts of behavior, breaking Liskov expectations.

### Comment Smells
- Comments restate the code rather than explain intent or constraints.
- Comments are outdated compared to the implementation.
- Large blocks of commented-out code retained instead of deleted.
- TODO/FIXME notes without owner, date, or plan for resolution.
- Comments justify known rule violations instead of fixing the underlying issue.
- Missing rationale for non-obvious trade-offs or deviations from standards.
- Documentation drift between headers/docstrings and actual behavior.

### Duplication Smells
- Copy-pasted logic across files instead of shared abstractions/utilities.
- Near-duplicate methods differing only by literals or trivial conditionals.
- Reimplemented standard library or existing helpers already available in the project.
- Repeated validation/business rules scattered instead of centralized.
- Duplicate constants or configuration values instead of a single source of truth.
- Parallel class hierarchies implementing the same workflow steps.
- Repeated SQL/queries differing only by filters that could be parameterized.

### Architecture Smells
- Tight coupling between modules prevents independent changes or testing.
- Circular dependencies between packages or layers.
- Global mutable state or singletons controlling core behavior.
- Layer violations (UI reaching into persistence or bypassing domain services).
- Temporal coupling: required call order not enforced by the API.
- Cross-cutting concerns (logging, retries, metrics) hand-rolled in multiple places instead of centralized.
- Hidden configuration defaults spread across code instead of explicit YAML-driven settings.

## Artifact Completeness (Blocking)
- Task document is self-contained: assumptions, scope boundaries, interfaces/contracts, explicit acceptance criteria, measurable success criteria.
- QA brief is self-contained: preconditions, explicit commands, expected results (pass/fail), validator roster, evidence links.
- Evidence paths are recorded in the task/QA docs, not just on disk.

## Task Completion Criteria
A task moves to `{{fn:task_state_dir("validated")}}/` only when:
1) Implementation is complete and documented in the task file.
2) Tests for new/changed code are present and passing.
3) Automation (type-check, lint, test, build or project equivalent) succeeds.
4) All blocking validators approve and QA sits in `{{fn:qa_state_dir("validated")}}/` (or project-equivalent state).
5) Task and QA documents are up to date with status, findings, and evidence links.

## Verification Command

Before marking any task as ready, run:

```bash
{{fn:ci_command("type-check")}} && {{fn:ci_command("lint")}} && {{fn:ci_command("test")}} && {{fn:ci_command("build")}}
```

All must pass with zero warnings.

## No-Mock Policy

NEVER mock critical internal services:
- Database clients - Use real database with test isolation strategies
- Authentication flows - Use real auth implementations
- HTTP route handlers - Test with real HTTP requests

Use real behavior assertions, not mock verifications. Forbidden assertions include spying on internal database client calls as proof of behavior (`toHaveBeenCalled` on database methods).

## Test Database Setup

Use project-configured test database isolation strategies:

```bash
# Check project-specific test setup in pack guidelines
# Typically involves containerized test databases or in-memory alternatives
```

Use project test utilities for database isolation (e.g., `withTestDatabase()`, `withSeededDatabase()`). Do not hand-roll DB management or transactions for isolation. Refer to active database pack guidelines for specific setup instructions.

## Banned Test Patterns

These patterns are FORBIDDEN in committed code:
- Skipped tests (any framework mechanism)
- Focused tests (any framework mechanism)
- Placeholder tests (e.g., TODO markers)
- Debug output in committed tests

Enforcement is project-specific (hooks/CI). Evidence must be generated by trusted runners, not manually fabricated.
