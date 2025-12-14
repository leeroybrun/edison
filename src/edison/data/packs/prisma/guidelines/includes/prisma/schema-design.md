# Schema Design Patterns

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
## Patterns

- Prefer stable primary keys (UUID/CUID) and keep them opaque.
- Use explicit relations with `@relation(fields:, references:)` and a deliberate `onDelete`.
- Use enums for constrained value sets.
- Add unique constraints and indexes for real query patterns (FKs + common filters + common sort keys).
- Keep nullability deliberate (nullable only when truly optional).

### Minimal illustrative schema (generic)

```prisma
model User {
  id      String   @id @default(uuid())
  email   String   @unique
  records Record[]
}

enum RecordStatus {
  ACTIVE
  INACTIVE
}

model Record {
  id        String       @id @default(uuid())
  name      String
  status    RecordStatus

  userId    String
  user      User         @relation(fields: [userId], references: [id], onDelete: Cascade)

  createdAt DateTime     @default(now())
  updatedAt DateTime     @updatedAt

  @@index([userId])
  @@index([status])
}
```

### Anti-patterns

- `status String` instead of an enum for a constrained domain
- Relations without indexes on foreign keys
- Making fields required before you have a safe backfill plan
<!-- /section: patterns -->

