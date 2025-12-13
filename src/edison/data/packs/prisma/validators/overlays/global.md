# global overlay for Prisma pack

<!-- extend: tech-stack -->
## Prisma Validation Context

### Guidelines
{{include:packs/prisma/guidelines/prisma/schema-design.md}}
{{include:packs/prisma/guidelines/prisma/migrations.md}}
{{include:packs/prisma/guidelines/prisma/query-optimization.md}}
{{include:packs/prisma/guidelines/prisma/relationships.md}}

### Concrete Checks
- Avoid N+1 queries; use `include`/`select` appropriately.
- Add indexes for frequently filtered fields.
- Use additive, reversible migrations; review for destructive changes.
- Ensure referential integrity and proper cascade semantics.
<!-- /extend -->
