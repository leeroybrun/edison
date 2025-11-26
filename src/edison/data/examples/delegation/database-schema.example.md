# Database Schema Delegation (database-architect)

## When to delegate
- New tables/collections are needed or existing schemas require breaking changes.
- Data contracts must be versioned and configured via YAML (naming, retention, limits).
- Migrations need to be planned, reversible, and validated against real engines (no mocks).
- Legacy columns/indexes should be removed or consolidated to keep the model coherent.

## Delegation prompt template
```
You are database-architect. Design/adjust schema for <domain>.
Context: <business rules, volume, SLAs>. Constraints: strict TDD, no mocks, config via YAML (<schema config path>), remove legacy tables/columns, reuse existing migration tooling.
Acceptance: <entities/fields/indexes/relations/constraints>; migration safety and rollback steps defined.
Deliverables: DDL/migrations + data-access updates + tests + docs. Run new tests.
Report: schema decisions, migration plan, tests run/results, risks/backfill steps.
```

## Expected deliverables
- Schema definition with constraints, indexes, and relationships aligned to requirements.
- Migrations that are idempotent, reversible, and scheduled/configured via YAML.
- Data-access layer updated to use new structures; legacy paths removed.
- Tests that exercise migrations and CRUD flows against real database adapters.
- Documentation covering config keys, rollout plan, backfill/cleanup strategy.

## Verification checklist
- YAML config drives names, limits, and feature toggles; no hardcoded DDL fragments.
- Migrations run forward/backward cleanly in test environment; data preserved or migrated correctly.
- Indexes and constraints match access patterns; performance and safety considered.
- Tests run and pass without mocks; fixtures create real tables/collections.
- Legacy schemas cleaned up; rollout/backfill plan documented with owner and timing.
