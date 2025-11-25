# database-architect-prisma (Prisma 6 / PostgreSQL 16)

## Tools
- Prisma schema at `apps/dashboard/prisma/schema.prisma` with PostgreSQL 16 datasource.
- `pnpm prisma migrate dev --name <change>` and `pnpm prisma generate`.
- `pnpm test --filter dashboard` to validate migrations against template DBs.

## Guidelines
- Prefix tables with `dashboard_` using `@@map` and prefer `@default(cuid())` IDs plus `createdAt/updatedAt` timestamps.
- Model relations with explicit foreign keys and supporting indexes; avoid unbounded cascades.
- Plan migrations for rollback safety; avoid destructive changes without backfill/guards.
- Use Context7 for Prisma 6/PostgreSQL 16 fresh patterns before changes; record markers.
- Keep performance in mind: add indexes for FK and common filters; analyze query plans when adding joins.

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

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  role      String

  // Relations
  leads     Lead[]

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("dashboard_users")
  @@index([email])
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

### Rollback Strategy

```bash
# Check current migration status
npx prisma migrate status

# Rollback last migration (manual process):
# 1. Revert schema.prisma changes
# 2. Delete migration folder
# 3. Mark as rolled back
npx prisma migrate resolve --rolled-back [migration-name]
```

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

**Index Guidelines**:
- Index foreign keys
- Index frequently filtered columns
- Index frequently sorted columns
- Use composite indexes for multi-column queries
- Don't over-index (slows down writes)

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

## Prisma TDD Patterns

### Testing Relationships

```typescript
import { prisma } from '@/lib/prisma'

describe('Lead-User relationship', () => {
  it('should load user with lead', async () => {
    const lead = await prisma.lead.findUnique({
      where: { id: testLeadId },
      include: { user: true }
    })

    expect(lead?.user).toBeDefined()
    expect(lead?.user.id).toBe(testUserId)
  })
})
```

### Testing Constraints

```typescript
it('should reject duplicate email', async () => {
  await prisma.lead.create({
    data: { email: 'test@example.com', /* ... */ }
  })

  await expect(
    prisma.lead.create({
      data: { email: 'test@example.com', /* ... */ }
    })
  ).rejects.toThrow('Unique constraint')
})
```

## One-to-Many Pattern (Prisma)

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

## Many-to-Many Pattern (Prisma)

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

## Data Integrity with Zod

```typescript
import { z } from 'zod'

// Zod schema for runtime validation (API layer)
export const leadSchema = z.object({
  name: z.string().min(1).max(255),
  email: z.string().email().optional(),
  status: z.enum(['DISCOVERED', 'ENGAGED', 'QUALIFIED']),
})

// Use in API routes
const validated = leadSchema.parse(requestBody)
await prisma.lead.create({ data: validated })
```
