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
A task moves to `tasks/validated/` only when:
1) Implementation is complete and documented in the task file.
2) Tests for new/changed code are present and passing.
3) Automation (type-check, lint, test, build or project equivalent) succeeds.
4) All blocking validators approve and QA sits in `qa/validated/` (or project-equivalent state).
5) Task and QA documents are up to date with status, findings, and evidence links.

## Verification Command

Before marking any task as ready, run:

```bash
<type-check-command> && <lint-command> && <test-command> && <build-command>
```

All must pass with zero warnings.

## Pre-commit Hook

The pre-commit hook runs:

```bash
node packages/qa-tools/bin/check-test-flags.mjs --staged
```

This prevents committing code with:
- `.skip()` or `.only()` in tests
- `.todo()` markers
- `console.log()` debug statements
- `@ts-ignore` or explicit `any` in staged TS files

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
- `.skip()` - No skipped tests
- `.only()` - No focused tests
- `.todo()` - No placeholder tests
- `console.log()` - No debug output

The pre-commit hook will block these. Evidence must be generated by trusted runners, not manually fabricated.

## Premium Design Standards

### Design Token System

Use design tokens for consistency:

```css
/* Spacing (8pt grid) */
--spacing-1: 0.25rem;  /* 4px */
--spacing-2: 0.5rem;   /* 8px */
--spacing-4: 1rem;     /* 16px */
--spacing-6: 1.5rem;   /* 24px */
--spacing-8: 2rem;     /* 32px */

/* Colors (semantic) */
--color-primary: theme('colors.blue.600');
--color-secondary: theme('colors.gray.600');
--color-success: theme('colors.green.600');
--color-warning: theme('colors.yellow.600');
--color-error: theme('colors.red.600');

/* Typography */
--font-sans: theme('fontFamily.sans');
--font-mono: theme('fontFamily.mono');
```

### Micro-interactions

All interactive elements must have:

1. **Hover states**: Subtle color/shadow change
2. **Focus states**: Visible focus ring (accessibility)
3. **Active states**: Pressed/clicked feedback
4. **Transitions**: Smooth 150-200ms transitions

```tsx
// Example: Button with micro-interactions
<button className="
  bg-primary hover:bg-primary-dark
  focus:ring-2 focus:ring-primary-light focus:outline-none
  active:scale-95
  transition-all duration-150
">
```

### Loading & Empty States

Every data-dependent component must handle:

1. **Loading state**: Skeleton or spinner
2. **Empty state**: Helpful message + action
3. **Error state**: Clear error + retry option

```tsx
function DataList({ data, isLoading, error }) {
  if (isLoading) return <Skeleton count={5} />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  if (data.length === 0) return <EmptyState message="No items yet" action={<CreateButton />} />;
  return <List items={data} />;
}
```

### Responsive Design

Breakpoints:
- Define breakpoints in the project's design system / configuration
- Prefer a small, consistent set (e.g. small / medium / large / extra-large)

Mobile-first approach:

```tsx
<div className="
  grid grid-cols-1
  sm:grid-cols-2
  lg:grid-cols-3
  xl:grid-cols-4
  gap-4
">
```

### Accessibility (WCAG AA)

Minimum requirements:
- Color contrast: 4.5:1 for text, 3:1 for large text
- Focus indicators: Visible on all interactive elements
- Keyboard navigation: All functionality accessible via keyboard
- Screen reader: Semantic HTML + ARIA where needed
- Reduced animations: Respect the OS/browser reduced-animation preference (via the appropriate media feature)

```tsx
<div style={/* disable transitions when reduced animations are requested */}>
```

### Dark Mode Support

All components must support dark mode:

```tsx
<div className="
  bg-white dark:bg-gray-900
  text-gray-900 dark:text-gray-100
  border-gray-200 dark:border-gray-700
">
```
