# API Testing Patterns

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
### API testing (Vitest)

- **Test the boundary**: Prefer exercising the real API boundary (real request/response) over calling internal helpers directly.
- **Assert contracts**: Status codes + response envelope shape + key fields.
- **Deterministic data**: Use per-test unique IDs / namespaces or transaction rollback (whatever your stack supports) to avoid cross-test collisions.
- **No internal mocking**: Do not mock internal auth/data/business modules as “proof”. If a boundary double is unavoidable, limit it to **external services you do not control**.

#### Minimal illustrative pattern (pseudocode)

```pseudocode
test("returns 400 on invalid input"):
  client = create_real_test_client()

  res = client.post("/api/v1/items", json={ name: "" })

  assert res.status == 400
  assert res.json.error == "Validation failed"
```

#### Anti-patterns

- Using `sleep()`/timeouts to “wait for consistency”
- Reusing static IDs across tests (not parallel-safe)
- Asserting internal call counts instead of observable outcomes
<!-- /section: patterns -->

