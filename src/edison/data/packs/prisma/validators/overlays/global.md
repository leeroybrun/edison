# global overlay for Prisma pack

<!-- EXTEND: TechStack -->
## Prisma Validation Context

### Guidelines
{{include:.edison/_generated/guidelines/prisma/schema-design.md}}
{{include:.edison/_generated/guidelines/prisma/migrations.md}}
{{include:.edison/_generated/guidelines/prisma/query-optimization.md}}
{{include:.edison/_generated/guidelines/prisma/relationships.md}}

### Concrete Checks
- Avoid N+1 queries; use `include`/`select` appropriately.
- Add indexes for frequently filtered fields.
- Use additive, reversible migrations; review for destructive changes.
- Ensure referential integrity and proper cascade semantics.
<!-- /EXTEND -->
