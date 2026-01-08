---
name: feature-implementer
pack: python
overlay_type: extend
---

<!-- extend: tools -->

### Python Development Tools

```bash
# Type checking (MANDATORY)
{{fn:ci_command("type-check")}}

# Linting
{{fn:ci_command("lint")}}

# Formatting
{{fn:ci_command("format")}}

# Testing with coverage
{{fn:ci_command("test-coverage")}}

# Tight iteration (TDD loop): run the smallest relevant scope
pytest tests/unit/test_module.py -v
pytest -k "test_feature" -v

# Reusable validation evidence (snapshot-based; reused when repo fingerprint unchanged)
edison evidence status <task-id>
edison evidence capture <task-id> --only test

# Install in development mode
pip install -e ".[dev]"

# Build package
{{fn:ci_command("build")}}
```

<!-- /extend -->

<!-- extend: guidelines -->

### Python implementation patterns

{{include-section:packs/python/guidelines/includes/python/PYTHON.md#patterns}}
{{include-section:packs/python/guidelines/includes/python/TYPING.md#patterns}}
{{include-section:packs/python/guidelines/includes/python/TESTING.md#patterns}}

<!-- /extend -->

<!-- extend: architecture -->

### Python architecture (minimal)

- Keep a small set of layers: `core/` (domain + services), adapters (db/files/http), entrypoints (cli/api).
- Push side-effects to edges; keep core easy to test.

<!-- /extend -->
