# TDD (Test-Driven Development)

> **Canonical Checklist:** The full condensed guidance lives at [./shared/TDD.md](./shared/TDD.md). This file surfaces the shared patterns for legacy references to this path.

## Patterns

### Pattern 1: Committed Data + Unique IDs

**Problem:** Tests fail randomly due to data collisions

**Solution:** Use unique identifiers and commit test data

1. Generate unique IDs for test entities
2. Commit data to database before assertions
3. Clean up in afterEach/afterAll

### Pattern 2: PostgreSQL Template Pool

**Problem:** Slow test setup due to migrations

**Solution:** Use template databases

1. Create template database once
2. Clone for each test
3. Drop clones after tests

Refer to the canonical checklist in `./shared/TDD.md` for the full RED→GREEN→REFACTOR loop, guardrails, and evidence requirements.
