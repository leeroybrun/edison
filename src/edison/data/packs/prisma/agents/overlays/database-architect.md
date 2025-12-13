# database-architect overlay for Prisma pack

<!-- extend: tools -->
- Prisma schema lives in your project's Prisma schema location (commonly `prisma/schema.prisma`).
- Run Prisma migrate/generate via your project's configured Prisma commands.
- Run your project's test suite to validate migrations against the test database strategy in use.
<!-- /extend -->

<!-- extend: guidelines -->
- Follow your project's table naming convention with `@@map` and prefer stable IDs plus `createdAt/updatedAt` timestamps.
- Model relations with explicit foreign keys and supporting indexes; avoid unbounded cascades.
- Plan migrations for rollback safety; avoid destructive changes without backfill/guards.
- Use Context7 for Prisma 6/PostgreSQL 16 fresh patterns before changes; record markers.
- Keep performance in mind: add indexes for FK and common filters; analyze query plans when adding joins.
<!-- /extend -->

<!-- section: PrismaSchemaPatterns -->
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

model Record {
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
  @@map("<project_prefix>_records")

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
<prisma-migrate-command> --name add_record_status_index

# 3. Verify migration SQL
cat prisma/migrations/[timestamp]_add_record_status_index/migration.sql

# 4. Test migration against template DBs
<test-command>

# 5. Commit schema + migration together
git add prisma/
git commit -m "feat: add record status index for faster filtering"
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
model Record {
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
const records = await prisma.record.findMany({
  select: {
    id: true,
    name: true,
    status: true,
  },
})

// BAD - Fetches all fields unnecessarily
const records = await prisma.record.findMany()

// GOOD - Use include for relations
const record = await prisma.record.findUnique({
  where: { id },
  include: {
    user: {
      select: { email: true, role: true },
    },
  },
})

// BAD - N+1 query problem
const records = await prisma.record.findMany()
for (const record of records) {
  const user = await prisma.user.findUnique({
    where: { id: record.userId },
  })
}
```

## Relationship Patterns

### One-to-Many Pattern

```prisma
model User {
  id    String @id @default(cuid())
  records Record[]  // One user has many records

  @@map("<project_prefix>_users")
}

model Record {
  id     String @id @default(cuid())
  userId String
  user   User @relation(fields: [userId], references: [id])

  @@map("<project_prefix>_records")
  @@index([userId])
}
```

### Many-to-Many Pattern

```prisma
model Record {
  id   String @id @default(cuid())
  tags RecordTag[]

  @@map("<project_prefix>_records")
}

model Tag {
  id    String @id @default(cuid())
  name  String @unique
  records RecordTag[]

  @@map("<project_prefix>_tags")
}

// Explicit join table for extra control
model RecordTag {
  recordId String
  tagId  String

  record Record @relation(fields: [recordId], references: [id], onDelete: Cascade)
  tag  Tag  @relation(fields: [tagId], references: [id], onDelete: Cascade)

  @@id([recordId, tagId])
  @@map("<project_prefix>_record_tags")
}
```
<!-- /section: PrismaSchemaPatterns -->





