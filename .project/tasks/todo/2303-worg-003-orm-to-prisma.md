<!-- TaskID: 2303-worg-003-orm-to-prisma -->
<!-- Priority: 2303 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: refactor -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave4 -->
<!-- EstimatedHours: 3 -->
<!-- DependsOn: Wave 3 -->

# WORG-003: Move ORM Patterns to Prisma Pack

## Summary
Move technology-generic ORM patterns from Wilson overlays to the Edison prisma pack.

## Problem Statement
Wilson overlays contain ORM patterns that are NOT Wilson-specific:
- Migration safety guidelines
- Query optimization patterns
- Transaction handling
- Soft delete implementation
- Audit field patterns

These should be in the prisma pack for all projects.

## Objectives
- [x] Identify ORM patterns in Wilson overlays
- [x] Move to Edison prisma pack
- [x] Keep Wilson schema specifics in overlays

## Source Files

### Wilson Overlays
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/
```

### Prisma Pack
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/prisma/guidelines/
```

## Precise Instructions

### Step 1: Audit Wilson Overlays
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays
grep -rn "prisma\|migration\|@default\|@@index\|soft.delete\|audit" . --include="*.md"
```

### Step 2: Content to Move

**Move to Prisma Pack:**
- Migration safety (destructive changes)
- Index optimization guidelines
- Soft delete pattern (deletedAt)
- Audit fields (createdAt, updatedAt)
- Transaction patterns
- Query optimization (include, select)
- N+1 prevention

**Keep in Wilson Overlays:**
- Wilson model definitions (Lead, Source)
- Wilson table prefix (dashboard_)
- Wilson-specific relationships

### Step 3: Update Prisma Pack

Add/update `edison/src/edison/packs/prisma/guidelines/`:

**query-optimization.md:**
```markdown
# Query Optimization

## Prevent N+1 Queries
Use `include` for related data:

```typescript
// Good
const users = await prisma.user.findMany({
  include: { posts: true }
});

// Bad - N+1
const users = await prisma.user.findMany();
for (const user of users) {
  const posts = await prisma.post.findMany({ where: { userId: user.id } });
}
```

## Select Only Needed Fields
```typescript
const users = await prisma.user.findMany({
  select: { id: true, name: true }
});
```
```

**schema-design.md (add):**
```markdown
## Audit Fields Pattern

Every table should have:
```prisma
model User {
  id        String   @id @default(uuid())
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  // ...fields
}
```

## Soft Delete Pattern
```prisma
model Post {
  id        String    @id
  deletedAt DateTime?

  @@index([deletedAt])
}
```

Query with soft delete:
```typescript
const posts = await prisma.post.findMany({
  where: { deletedAt: null }
});
```
```

**migrations.md (add):**
```markdown
## Migration Safety

### Destructive Changes
NEVER in production:
- DROP COLUMN with data
- Change type with data loss
- Remove NOT NULL without default

### Safe Pattern
1. Add new column (nullable)
2. Migrate data
3. Add NOT NULL constraint
4. Remove old column (next release)

### Large Table Migrations
Use batched updates:
```sql
-- Instead of one large UPDATE
UPDATE users SET new_col = old_col WHERE id IN (
  SELECT id FROM users WHERE new_col IS NULL LIMIT 1000
);
```
```

### Step 4: Update Wilson Overlays

Keep only:
```markdown
# Wilson Prisma Overlay

## Schema Location
apps/dashboard/prisma/schema.prisma

## Table Prefix
All tables use `dashboard_` prefix via @@map

## Core Models
- Lead (main entity)
- Source (lead origin)
- ProcessedItem (sync tracking)
```

## Verification Checklist
- [ ] Migration safety in prisma pack
- [ ] Query optimization in prisma pack
- [ ] Audit/soft delete patterns in pack
- [ ] Wilson overlays only have model specifics

## Success Criteria
Any project using prisma pack gets ORM best practices.
