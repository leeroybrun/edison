# Migration Safety

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
## Patterns

- Prefer **additive** changes (new tables/columns/indexes) over destructive edits.
- Keep migrations small, reviewable, and staged when changing constraints.
- Always validate migration safety with a preview of the generated SQL (per repo’s Prisma workflow).

### Safe staged change (nullable → required)

```pseudocode
1) Add new column as NULLABLE
2) Backfill deterministically (one-time script or migration step)
3) Deploy code that reads/writes the new column
4) Make column REQUIRED in a follow-up migration
```

### Anti-patterns

- Dropping/renaming columns in one step without an explicit rollout/backfill plan
- Making a column required immediately when existing rows violate it
- Adding unique constraints without auditing existing duplicates
<!-- /section: patterns -->

