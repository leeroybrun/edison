---
name: code-reviewer
pack: python
overlay_type: extend
---

<!-- extend: tools -->

### Python Review Tools

```bash
# Type checking
{{function:ci_command("type-check")}}

# Linting
{{function:ci_command("lint")}}

# Format check
{{function:ci_command("format-check")}}

# Run tests
{{function:ci_command("test")}}

# Check coverage
{{function:ci_command("test-coverage")}}

# Security scan (if bandit installed)
bandit -r src/

# Complexity check
radon cc src/ -a
```

<!-- /extend -->

<!-- extend: guidelines -->

### Python Code Review Checklist

{{include-section:packs/python/guidelines/includes/python/PYTHON.md#patterns}}
{{include-section:packs/python/guidelines/includes/python/TYPING.md#patterns}}
{{include-section:packs/python/guidelines/includes/python/TESTING.md#patterns}}

1. **Type Safety**
   - [ ] All functions have type annotations
   - [ ] mypy --strict passes with 0 errors
   - [ ] No `Any` without justification
   - [ ] No `# type: ignore` without comment
   - [ ] Generics used correctly (TypeVar, Protocol)

2. **Testing (NO MOCKS)**
   - [ ] Follow the core NO MOCKS policy (mock only system boundaries)
   - [ ] Real files/databases used
   - [ ] pytest fixtures for setup
   - [ ] Edge cases parametrized
   - [ ] All tests passing

3. **Modern Python**
   - [ ] Python 3.12+ patterns
   - [ ] `list[T]` not `List[T]`
   - [ ] `T | None` not `Optional[T]`
   - [ ] dataclasses for data
   - [ ] Protocol for duck typing
   - [ ] pathlib for paths

4. **Code Quality**
   - [ ] ruff check passes
   - [ ] Consistent naming (snake_case)
   - [ ] No commented-out code
   - [ ] No TODO/FIXME in production
   - [ ] Docstrings on public APIs

5. **Configuration**
   - [ ] No hardcoded values
   - [ ] Config from YAML
   - [ ] Secrets from env vars only

6. **Error Handling**
   - [ ] Custom exceptions defined
   - [ ] No bare `except:`
   - [ ] Proper exception messages
   - [ ] Resources cleaned up

7. **Architecture**
   - [ ] Clear module boundaries
   - [ ] No circular imports
   - [ ] Single responsibility
   - [ ] Dependency injection

### Review Output Format

```markdown
## Python Code Review

### Type Checking
- [ ] mypy --strict: PASS/FAIL
- Issues: [list specific issues with file:line]

### Testing
- [ ] No mocks: PASS/FAIL
- [ ] All tests passing: PASS/FAIL
- Issues: [list test issues]

### Modern Python
- Issues: [list outdated patterns]

### Code Quality
- [ ] ruff check: PASS/FAIL
- Issues: [list quality issues]

### Verdict
- [ ] APPROVED
- [ ] APPROVED WITH WARNINGS
- [ ] REJECTED
```

<!-- /extend -->
