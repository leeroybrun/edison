# global overlay for Prisma pack

<!-- extend: tech-stack -->
## Prisma Validation Context

### Guidelines
{{include-section:packs/prisma/guidelines/includes/prisma/schema-design.md#patterns}}
{{include-section:packs/prisma/guidelines/includes/prisma/migrations.md#patterns}}
{{include-section:packs/prisma/guidelines/includes/prisma/query-optimization.md#patterns}}
{{include-section:packs/prisma/guidelines/includes/prisma/relationships.md#patterns}}

### Concrete Checks
- Avoid N+1 queries; use `include`/`select` appropriately.
- Add indexes for frequently filtered fields.
- Use additive, reversible migrations; review for destructive changes.
- Ensure referential integrity and proper cascade semantics.
<!-- /extend -->
