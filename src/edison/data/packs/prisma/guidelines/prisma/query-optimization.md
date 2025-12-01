# Query Optimization

- Select only required fields with `select`.
- Use pagination for large result sets; avoid unbounded scans.
- Preload relations with `include` to avoid N+1 patterns.
- In Prisma 6, use `$transaction` for multi-entity updates or sequences that must be atomic, and prefer `findUnique` with typed selectors over broad `findMany` scans.
