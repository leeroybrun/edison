# Prisma Testing

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
## Patterns

- Use a **real database** in tests (no mocking Prisma as a substitute for behavior).
- Ensure **isolation** between tests using one of:
  - Transaction rollback per test
  - Ephemeral database per test run (container / temp DB)
  - Deterministic cleanup by scoping created records to a per-test unique identifier
- Keep tests deterministic: avoid wall-clock sleeps and uncontrolled randomness.

### Minimal illustrative pattern (pseudocode)

```pseudocode
test("creates and reads record"):
  db = connect_real_test_database()
  begin_transaction()

  created = db.record.create({ name: "x", status: ACTIVE })
  fetched = db.record.findUnique(created.id)

  assert fetched.name == "x"

  rollback_transaction()
```

### Anti-patterns

- Mocking Prisma client and asserting call counts
- Sharing a database namespace/ID across tests (not parallel-safe)
- Leaving test data behind without cleanup or rollback
<!-- /section: patterns -->
