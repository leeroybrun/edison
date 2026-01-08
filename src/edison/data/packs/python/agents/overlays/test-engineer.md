---
name: test-engineer
pack: python
overlay_type: extend
---

<!-- extend: tools -->

### Python Testing Tools

```bash
# Run all tests
{{fn:ci_command("test")}}

# Run with coverage
{{fn:ci_command("test-coverage")}}

# Tight iteration (TDD loop): run the smallest relevant scope
pytest tests/unit/test_module.py -v
pytest -k "test_create" -v
pytest -m "not slow" -v

# Reusable validation evidence (snapshot-based; reused when repo fingerprint unchanged)
edison evidence status <task-id>
edison evidence capture <task-id> --only test

# Run with verbose output
pytest tests/ -v --tb=long

# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Type check test files
mypy tests/
```

<!-- /extend -->

<!-- extend: guidelines -->

### Python testing patterns

{{include-section:packs/python/guidelines/includes/python/TESTING.md#patterns}}
{{include-section:packs/python/guidelines/includes/python/ASYNC.md#patterns}}

<!-- /extend -->
