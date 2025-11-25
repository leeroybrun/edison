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
