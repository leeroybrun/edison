# database-architect overlay for Prisma pack

<!-- extend: tools -->
- Prisma schema lives in your project's Prisma schema location (commonly `prisma/schema.prisma`).
- Run Prisma migrate/generate via your project's configured Prisma commands.
- Run your project's test suite to validate migrations against the test database strategy in use.
<!-- /extend -->

<!-- extend: guidelines -->
- Apply Prisma patterns for schema design, relationships, migrations, and query optimization.
{{include-section:packs/prisma/guidelines/includes/prisma/schema-design.md#patterns}}
{{include-section:packs/prisma/guidelines/includes/prisma/relationships.md#patterns}}
{{include-section:packs/prisma/guidelines/includes/prisma/migrations.md#patterns}}
{{include-section:packs/prisma/guidelines/includes/prisma/query-optimization.md#patterns}}
{{include-section:packs/prisma/guidelines/includes/prisma/TESTING.md#patterns}}
<!-- /extend -->





