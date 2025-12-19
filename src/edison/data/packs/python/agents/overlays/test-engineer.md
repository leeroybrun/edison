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

# Run specific test file
pytest tests/unit/test_module.py -v

# Run tests matching pattern
pytest -k "test_create" -v

# Run only marked tests
pytest -m "not slow" -v

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
