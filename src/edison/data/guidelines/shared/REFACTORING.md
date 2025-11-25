# Refactoring Guidelines (Generic, Core)

Version: 1.0
Last Updated: 2025-11-18
Scope: Project-agnostic guidance for safe, incremental refactoring with SOLID/DRY emphasis.

---

## Purpose

Refactoring improves internal structure without changing observable behavior. It reduces
complexity, removes duplication (DRY), aligns code with SOLID, and increases maintainability.
Refactoring is performed continuously, preferably as part of the TDD loop (RED → GREEN → REFACTOR).

---

## Safety Principles

**DO:**
- ✅ Keep behavior equivalent; verify with tests at each step.
- ✅ Work in very small steps; commit frequently.
- ✅ Prefer pure functions and explicit dependencies to isolate change.
- ✅ Remove duplication systematically; extract abstractions after three instances (rule of three).
- ✅ Strengthen naming; let names reveal intent.
- ✅ Apply SOLID to reduce coupling and increase cohesion.

**DON'T:**
- ❌ Mix refactoring with feature changes in the same commit.
- ❌ Change public APIs without deprecation or adapters.
- ❌ Rename and move and rewrite at once; separate concerns.
- ❌ Defer tests; they are the safety net.
- ❌ Introduce cleverness that hides intent.

---

## Workflow (TDD alignment)

1) RED: capture the desired behavior with a failing test.
2) GREEN: write the minimal code to make it pass.
3) REFACTOR: improve structure while keeping all tests green.

```pseudo
# Example cadence
write_failing_test()
minimal_implementation()
refactor_names_extract_functions()
run_all_tests()
```

---

## Refactoring Patterns

- Extract Function / Method
- Introduce Parameter Object
- Replace Conditional with Polymorphism
- Extract Interface (DIP)
- Invert Dependencies (DIP)
- Move Responsibility (SRP)
- Encapsulate Collection
- Replace Temp with Query
- Decompose Conditional
- Remove Dead Code
- Inline Variable / Function (when name adds no value)
- Rename for Intent
- Extract Module / Package
- Separate Commands from Queries (CQS)
- Introduce Domain Language (ubiquitous vocabulary)

```pseudo
# Before
function price(items, taxRate) {
  // calculate subtotal, apply discounts, apply tax, format
}

# After
function subtotal(items) { /* ... */ }
function discount(subtotal) { /* ... */ }
function tax(amount, rate) { /* ... */ }
function price(items, taxRate) { return tax(discount(subtotal(items)), taxRate) }
```

---

## SOLID During Refactors

- SRP: Give each unit one clear reason to change.
- OCP: Add behavior by extension, not modification (strategy, plugins).
- LSP: Respect substitutability; avoid tightening preconditions or loosening postconditions.
- ISP: Keep interfaces small and specific; avoid fat interfaces.
- DIP: Depend on abstractions; inject collaborators.

```pseudo
# DIP example via constructor injection
interface Clock { now(): Instant }
class Session(clock: Clock) { /* ... */ }
```

---

## DRY and Duplication Tax

- Track duplication hotspots; eliminate near-duplicates with shared helpers.
- Consolidate validation rules and mapping logic.
- Extract cross-cutting patterns (logging, error handling) into utilities.
- Prefer composition utilities to inheritance hierarchies.

```pseudo
# Repeated parsing replaced with a single, tested helper
function parseAmount(s) { /* trims, validates, converts, returns result */ }
```

---

## Branching Strategy

- Prefer short-lived branches for refactors.
- Rebase frequently to avoid large merges.
- Keep refactor-only PRs scoped and easy to review.

---

## Measuring Progress

- Complexity metrics trend downward (per function/module).
- Diff size remains small; reviewable in minutes, not hours.
- Test runtime stable or improved.
- Coupling reduced; modules easier to change independently.

---

## Brownfield Techniques

- Strangle pattern: wrap legacy logic with a clean interface; replace incrementally.
- Characterization tests: lock current behavior before modifying internals.
- Anti-corruption layer: protect the core model from legacy external conventions.
- Facade: provide a minimal surface for consumers while reworking internals.

```pseudo
# Characterization test captures current (even if odd) behavior
assert legacy_parse("  1,2  ") == ["1","2"]
```

---

## Naming and Intent

- Prefer domain terms; avoid generic names (data, info, handle).
- Names should read like documentation; avoid abbreviations.
- Keep functions short and verbs strong (parse, compute, validate, persist).

---

## Error Handling and Contracts

- Fail fast with clear, actionable messages.
- Normalize inputs at module boundaries.
- Use total functions where possible (handle all inputs).
- Avoid hidden global state; make effects explicit.

```pseudo
if (!isValid(input)) {
  return Err("Invalid customer ID: must be UUID")
}
```

---

## Testing Support

- Add tests before risky changes; expand edge cases.
- Prefer property-based tests for parsers and converters.
- Use golden files for stable, textual outputs.
- Avoid mocking at boundaries; test real I/O via adapters.

```pseudo
# Property-based example
for all amount in valid_amounts():
  assert parseAmount(formatAmount(amount)) == amount
```

---

## Migration and Deprecation

- Provide shims/adapters for renamed functions.
- Mark deprecations with timelines; remove in scheduled cleanups.
- Communicate changes early to consumers.

---

## Checklist

- [ ] Behavior preserved; tests remain green
- [ ] Smaller, clearer functions and modules
- [ ] Names reflect intent; comments reduced
- [ ] Duplication removed; helpers extracted (DRY)
- [ ] Dependencies injected; global state reduced (SOLID/DIP)
- [ ] Error messages precise and actionable
- [ ] Edge cases covered with tests

---

## Examples (additional)

```pseudo
# Replace magic numbers with named constants
const MAX_RETRY = 3
```

```pseudo
# Replace boolean flags with specific functions
function exportCSV() { /* ... */ }
function exportJSON() { /* ... */ }
```

```pseudo
# Replace diagram: monolith → modular packages
core /
util /
cli  /
```

---

## Anti‑Patterns

- Large, unreviewable refactor PRs
- Refactors without tests
- Clever abstractions with unclear names
- Inconsistent error handling scattered across codebase
- Catch-all exceptions that hide root causes

---

## References

- Refactoring (Fowler)
- Clean Architecture (Martin)
- Working Effectively with Legacy Code (Feathers)
- A Philosophy of Software Design (Ousterhout)

