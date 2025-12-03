---
name: feature-implementer
pack: python
overlay_type: extend
---

<!-- EXTEND: Tools -->

### Python Development Tools

```bash
# Type checking (MANDATORY)
mypy --strict src/

# Linting
ruff check src/ tests/

# Formatting
ruff format src/ tests/

# Testing with coverage
pytest tests/ -v --tb=short --cov=src

# Run specific test file
pytest tests/unit/test_module.py -v

# Run tests matching pattern
pytest -k "test_feature" -v

# Install in development mode
pip install -e ".[dev]"

# Build package
python -m build
```

<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->

### Python-Specific Implementation Guidelines

1. **Modern Python (3.12+)**
   - Use `list[T]` not `List[T]`
   - Use `T | None` not `Optional[T]`
   - Use dataclasses for data structures
   - Use Protocol for duck typing
   - Use pathlib.Path for file paths

2. **Type Hints (MANDATORY)**
   - All functions must have type annotations
   - mypy --strict must pass with 0 errors
   - Use `from __future__ import annotations`
   - Document `# type: ignore` with reason

3. **Testing (NO MOCKS)**
   - Use real files with tmp_path fixture
   - Use real databases (SQLite for tests)
   - Use pytest fixtures for setup
   - Parametrize edge cases

4. **Configuration**
   - All config from YAML files
   - No hardcoded values
   - Environment variables for secrets only

### Python File Structure

```
src/
  package_name/
    __init__.py           # Public API only
    py.typed              # PEP 561 marker
    core/
      models.py           # Dataclasses
      services.py         # Business logic
    cli/
      main.py             # Entry point
tests/
  unit/
  integration/
  conftest.py
```

<!-- /EXTEND -->

<!-- EXTEND: Architecture -->

### Python Architecture Patterns

**Layered Architecture:**
- **Models Layer**: Pure data (dataclasses, enums)
- **Services Layer**: Business logic (stateless functions)
- **Repository Layer**: Data access (file I/O, database)
- **CLI Layer**: User interface (argparse, click)

**Dependency Injection:**
```python
class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def get_task(self, id: str) -> Task | None:
        return self._repository.get(id)
```

**Error Handling:**
```python
class DomainError(Exception):
    """Base exception for domain errors."""
    pass

class ValidationError(DomainError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"{field}: {message}")
```

<!-- /EXTEND -->
