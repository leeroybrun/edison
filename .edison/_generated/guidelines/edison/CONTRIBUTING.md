# Edison Contributing Guide

This guide explains how to contribute to Edison following its own principles.

---

## Before You Start

### Read CLAUDE.md

The `CLAUDE.md` file defines 16 critical principles. Key ones:

1. **STRICT TDD**: Write failing test FIRST, then implement
2. **NO MOCKS**: Test real behavior with real code
3. **NO HARDCODING**: All config from YAML
4. **DRY**: Zero code duplication
5. **NO LEGACY**: Delete old code completely

### Understand the Architecture

Read `.edison/guidelines/ARCHITECTURE.md` to understand:
- Module structure
- Key patterns (auto-discovery, configuration, entities, state machines, composition)
- How to add new features

---

## Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/edison.git
cd edison

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode
pip install -e ".[dev]"

# Verify installation
edison --help
```

---

## Development Workflow

### 1. Create Branch

```bash
git checkout -b feature/your-feature
```

### 2. Write Failing Test First (TDD RED)

```python
# tests/unit/test_new_feature.py
def test_new_feature_does_expected_thing():
    result = new_feature(input_data)
    assert result == expected_output
```

```bash
pytest tests/unit/test_new_feature.py -v
# Expected: FAILED (test should fail initially)
```

### 3. Implement Minimal Code (TDD GREEN)

```python
# src/edison/core/new_feature.py
def new_feature(data: InputType) -> OutputType:
    # Minimal implementation to pass test
    return expected_output
```

```bash
pytest tests/unit/test_new_feature.py -v
# Expected: PASSED
```

### 4. Refactor and Add Types (TDD REFACTOR)

```python
from __future__ import annotations

def new_feature(
    data: InputType,
    *,
    option: bool = False,
) -> OutputType:
    """Process data with new feature.

    Args:
        data: Input data to process
        option: Enable optional behavior

    Returns:
        Processed output
    """
    # Clean implementation
    return process(data, option)
```

### 5. Verify All Quality Checks

```bash
# Type check
mypy --strict src/edison/

# Lint
ruff check src/edison/ tests/

# All tests
pytest tests/ -v --tb=short

# Coverage (aim for high coverage)
pytest tests/ --cov=src/edison --cov-report=term-missing
```

---

## Code Style

### Type Hints (MANDATORY)

```python
from __future__ import annotations
from typing import TypeVar, Protocol

T = TypeVar("T")

def process(items: list[T]) -> list[T]:
    """Process items."""
    return [transform(item) for item in items]
```

### Modern Python (3.12+)

```python
# Use modern syntax
def get_value(key: str) -> str | None:  # Not Optional[str]
    return cache.get(key)

items: list[str] = []  # Not List[str]

@dataclass(frozen=True, slots=True)
class Entity:
    id: str
```

### No Hardcoding

```python
# BAD
TIMEOUT = 30
API_URL = "https://api.example.com"

# GOOD
from edison.core.config import ConfigManager
config = ConfigManager()
timeout = config.get("session.timeout")
```

### No Mocks

```python
# BAD
from unittest.mock import Mock, patch

@patch("module.function")
def test_with_mock(mock_func): ...

# GOOD
def test_with_real_file(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("key: value\n")

    result = load_config(config)
    assert result["key"] == "value"
```

---

## Adding Features

### New CLI Command

1. Create `src/edison/cli/{domain}/{command}.py`:
   ```python
   def register_args(parser: argparse.ArgumentParser) -> None:
       parser.add_argument("--option", help="Description")

   def main(args: argparse.Namespace) -> int:
       # Implementation
       return 0
   ```

2. Add tests in `tests/unit/cli/test_{command}.py`

3. Command is auto-discovered (no registration needed)

### New Configuration

1. Add to YAML in `src/edison/data/config/`
2. Create/update domain accessor in `src/edison/core/config/domains/`
3. Use accessor in code (never hardcode values)

### New Pack

1. Copy template: `cp -r src/edison/data/packs/_template src/edison/data/packs/new_pack`
2. Edit `pack.yml` with:
   - Name, version, description
   - File pattern triggers
   - Validators, guidelines, agents
3. Create agent overlays in `agents/overlays/`
4. Create validator overlays in `validators/overlays/`
5. Add guidelines
6. Test: `edison compose all`

---

## Testing

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (fast)
│   ├── core/
│   ├── cli/
│   └── conftest.py
├── integration/             # Integration tests
│   └── conftest.py
├── e2e/                     # End-to-end tests
│   └── conftest.py
└── fixtures/                # Test data
```

### Writing Tests

```python
import pytest
from pathlib import Path

@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Create real config file."""
    config = tmp_path / "config.yaml"
    config.write_text("key: value\n")
    return config

def test_load_config(config_file: Path):
    """Test loading from real file."""
    config = load_config(config_file)
    assert config["key"] == "value"

@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("", False),
])
def test_validate(input: str, expected: bool):
    """Test validation edge cases."""
    assert validate(input) == expected
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/unit/core/test_config.py -v

# With coverage
pytest tests/ --cov=src/edison --cov-report=term-missing

# Only fast tests (skip slow)
pytest tests/ -m "not slow"
```

---

## Pull Request Checklist

Before submitting:

- [ ] Tests written first (TDD)
- [ ] All tests passing
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] No mocks used
- [ ] No hardcoded values
- [ ] Config added to YAML (if needed)
- [ ] Documentation updated (if needed)
- [ ] Follows existing patterns

---

## Common Issues

### "mypy: No module named..."

```bash
pip install -e ".[dev]"
```

### "Test using mock detected"

Replace mocks with real implementations:
- Use `tmp_path` fixture for files
- Use SQLite for database tests
- Use TestClient for API tests

### "Hardcoded value detected"

Move value to YAML config and use accessor:
```python
from edison.core.config import ConfigManager
config = ConfigManager()
value = config.get("section.key")
```

---

## Getting Help

- Read existing code for patterns
- Check `.edison/guidelines/` for guides
- Review test examples in `tests/`
- Ask in discussions/issues

---

## Summary

1. **TDD**: Tests first, always
2. **No Mocks**: Real behavior
3. **No Hardcoding**: YAML config
4. **Type Hints**: mypy --strict
5. **Follow Patterns**: Match existing code
6. **Complete Implementation**: No TODOs