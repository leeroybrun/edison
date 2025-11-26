# database-architect overlay for Prisma pack

<!-- EXTEND: Tools -->
- Prisma schema at `apps/dashboard/prisma/schema.prisma` with PostgreSQL 16 datasource.
- `pnpm prisma migrate dev --name <change>` and `pnpm prisma generate`.
- `pnpm test --filter dashboard` to validate migrations against template DBs.
<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->
- Prefix tables with `dashboard_` using `@@map` and prefer `@default(cuid())` IDs plus `createdAt/updatedAt` timestamps.
- Model relations with explicit foreign keys and supporting indexes; avoid unbounded cascades.
- Plan migrations for rollback safety; avoid destructive changes without backfill/guards.
- Use Context7 for Prisma 6/PostgreSQL 16 fresh patterns before changes; record markers.
- Keep performance in mind: add indexes for FK and common filters; analyze query plans when adding joins.
<!-- /EXTEND -->

<!-- NEW_SECTION: PrismaSchemaPatterns -->
## Prisma Schema Patterns

### Schema Structure

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model Lead {
  id            String   @id @default(cuid())
  name          String
  email         String?  @unique
  status        String   // Use enum pattern
  sourceUrl     String   @unique

  // Foreign keys - ALWAYS explicit
  userId        String
  user          User @relation(fields: [userId], references: [id])

  // Timestamps - ALWAYS include
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt

  // Table name with project prefix
  @@map("dashboard_leads")

  // Indexes - FK + frequently queried
  @@index([status])
  @@index([userId])
  @@index([createdAt])
}
```

### Critical Patterns

1. **Table Naming**: ALWAYS use `@@map("prefix_[table]")` for project prefixing
2. **IDs**: Use `@default(cuid())` for primary keys (collision-safe)
3. **Timestamps**: Always include `createdAt` and `updatedAt`
4. **Relations**: Use explicit foreign keys with `@relation(fields:, references:)`
5. **Indexes**: Add for foreign keys, frequently queried fields, sort columns

## Migration Workflow

### Creating Migrations

```bash
# 1. Update schema.prisma
# ... make schema changes ...

# 2. Create migration (generates SQL)
npx prisma migrate dev --name add_lead_status_index

# 3. Verify migration SQL
cat prisma/migrations/[timestamp]_add_lead_status_index/migration.sql

# 4. Test migration against template DBs
npm test

# 5. Commit schema + migration together
git add prisma/
git commit -m "feat: add lead status index for faster filtering"
```

### Migration Safety

**Safe Operations** (can run in production):
- Adding nullable columns
- Adding indexes (with `CONCURRENTLY` in raw SQL)
- Adding new tables
- Adding new relations (nullable)

**Dangerous Operations** (require special handling):
- Removing columns - verify no code references first
- Renaming columns - requires multi-step migration
- Changing column types - may lose data
- Adding non-nullable columns - need default or backfill

## Performance Optimization

### Index Strategy

```prisma
model Lead {
  // ... fields ...

  // Single-column indexes
  @@index([status])           // Filter by status
  @@index([createdAt])        // Sort by date
  @@index([userId])           // Filter by user (foreign key)

  // Composite indexes (column order matters!)
  @@index([userId, status])   // Filter by user AND status
  @@index([status, createdAt]) // Filter by status, sort by date
}
```

### Query Optimization

```typescript
// GOOD - Use select to limit fields
const leads = await prisma.lead.findMany({
  select: {
    id: true,
    name: true,
    status: true,
  },
})

// BAD - Fetches all fields unnecessarily
const leads = await prisma.lead.findMany()

// GOOD - Use include for relations
const lead = await prisma.lead.findUnique({
  where: { id },
  include: {
    user: {
      select: { email: true, role: true },
    },
  },
})

// BAD - N+1 query problem
const leads = await prisma.lead.findMany()
for (const lead of leads) {
  const user = await prisma.user.findUnique({
    where: { id: lead.userId },
  })
}
```

## Relationship Patterns

### One-to-Many Pattern

```prisma
model User {
  id    String @id @default(cuid())
  leads Lead[]  // One user has many leads

  @@map("dashboard_users")
}

model Lead {
  id     String @id @default(cuid())
  userId String
  user   User @relation(fields: [userId], references: [id])

  @@map("dashboard_leads")
  @@index([userId])
}
```

### Many-to-Many Pattern

```prisma
model Lead {
  id   String @id @default(cuid())
  tags LeadTag[]

  @@map("dashboard_leads")
}

model Tag {
  id    String @id @default(cuid())
  name  String @unique
  leads LeadTag[]

  @@map("dashboard_tags")
}

// Explicit join table for extra control
model LeadTag {
  leadId String
  tagId  String

  lead Lead @relation(fields: [leadId], references: [id], onDelete: Cascade)
  tag  Tag  @relation(fields: [tagId], references: [id], onDelete: Cascade)

  @@id([leadId, tagId])
  @@map("dashboard_lead_tags")
}
```
<!-- /NEW_SECTION -->

