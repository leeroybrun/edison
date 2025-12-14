# Query Optimization

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
## Patterns

- Select only required fields with `select`.
- Use pagination for large result sets; avoid unbounded scans.
- Preload relations with `include` (or `select` nested) to avoid N+1 patterns.
- Use `$transaction` for multi-entity updates that must be atomic.

### N+1 (BAD) vs preload (GOOD)

```typescript
// ❌ BAD: N+1 queries
const records = await prisma.record.findMany()
for (const record of records) {
  await prisma.user.findUnique({ where: { id: record.userId } })
}
```

```typescript
// ✅ GOOD: preload relation
const records = await prisma.record.findMany({
  include: { user: { select: { id: true, email: true } } },
})
```

### Narrow selects

```typescript
// ✅ GOOD: narrow select
const records = await prisma.record.findMany({
  select: { id: true, name: true, createdAt: true },
  orderBy: { createdAt: 'desc' },
  take: 20,
})
```
<!-- /section: patterns -->
