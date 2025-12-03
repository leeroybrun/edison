---
name: code-reviewer
pack: python
overlay_type: extend
---

<!-- EXTEND: Tools -->

### Python Review Tools

```bash
# Type checking
mypy --strict src/

# Linting
ruff check src/ tests/

# Format check
ruff format --check src/ tests/

# Run tests
pytest tests/ -v --tb=short

# Check coverage
pytest tests/ --cov=src --cov-report=term-missing

# Security scan (if bandit installed)
bandit -r src/

# Complexity check
radon cc src/ -a
```

<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->

### Python Code Review Checklist

1. **Type Safety**
   - [ ] All functions have type annotations
   - [ ] mypy --strict passes with 0 errors
   - [ ] No `Any` without justification
   - [ ] No `# type: ignore` without comment
   - [ ] Generics used correctly (TypeVar, Protocol)

2. **Testing (NO MOCKS)**
   - [ ] No mock usage (per CLAUDE.md)
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

### Type Safety
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

<!-- /EXTEND -->
