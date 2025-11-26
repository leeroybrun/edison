# Prisma Validation Context

{{include:.edison/packs/prisma/guidelines/schema-design.md}}
{{include:.edison/packs/prisma/guidelines/migrations.md}}
{{include:.edison/packs/prisma/guidelines/query-optimization.md}}
{{include:.edison/packs/prisma/guidelines/relationships.md}}

## Concrete Checks
- Avoid N+1 queries; use `include`/`select` appropriately.
- Add indexes for frequently filtered fields.
- Use additive, reversible migrations; review for destructive changes.
- Ensure referential integrity and proper cascade semantics.

