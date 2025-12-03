# Python Testing Guide

Comprehensive guide for pytest-based testing with NO MOCKS policy.

---

## Core Principle: NO MOCKS

Per CLAUDE.md: **NO MOCKS EVER** - Test real behavior with real code.

```python
# BAD: Mocking
from unittest.mock import Mock, patch

@patch("module.external_service")
def test_with_mock(mock_service):
    mock_service.return_value = {"status": "ok"}
    result = process()
    assert result == "ok"

# GOOD: Real behavior
def test_with_real_service(temp_config: Path):
    """Test with actual config file."""
    config = load_config(temp_config)
    result = process(config)
    assert result == "ok"
```

---

## pytest Configuration

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "-ra",
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
]
asyncio_mode = "auto"
```

---

## Test Organization

### Directory Structure

```
tests/
  conftest.py              # Shared fixtures
  unit/                    # Unit tests (fast, isolated)
    conftest.py
    test_models.py
    test_services.py
  integration/             # Integration tests
    conftest.py
    test_database.py
    test_api.py
  e2e/                     # End-to-end tests
    conftest.py
    test_workflow.py
  fixtures/                # Test data files
    config.yaml
    sample_data.json
```

### Naming Conventions

```python
# Test file: test_{module}.py
# test_task_service.py

# Test function: test_{behavior}_{scenario}
def test_create_task_with_valid_data():
    ...

def test_create_task_fails_with_empty_title():
    ...

def test_get_task_returns_none_when_not_found():
    ...
```

---

## Fixtures

### Basic Fixtures

```python
import pytest
from pathlib import Path

@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test files."""
    return tmp_path

@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Create a real config file for testing."""
    config = tmp_path / "config.yaml"
    config.write_text("""
settings:
  timeout: 30
  debug: true
""")
    return config
```

### Fixture Scope

```python
@pytest.fixture(scope="session")
def database():
    """Create test database once per session."""
    db = create_test_database()
    yield db
    db.cleanup()

@pytest.fixture(scope="module")
def api_client():
    """Create API client once per module."""
    return APIClient(base_url="http://localhost:8000")

@pytest.fixture  # Default: function scope
def task():
    """Create fresh task for each test."""
    return Task(id="test-1", title="Test Task")
```

### Factory Fixtures

```python
@pytest.fixture
def make_task():
    """Factory fixture for creating tasks with custom attributes."""
    def _make_task(
        id: str = "test-1",
        title: str = "Test Task",
        status: str = "pending",
    ) -> Task:
        return Task(id=id, title=title, status=status)

    return _make_task

def test_with_factory(make_task):
    task1 = make_task(id="1", title="First")
    task2 = make_task(id="2", status="completed")
    assert task1.id != task2.id
```

---

## Real Behavior Testing (No Mocks)

### File System Tests

```python
def test_load_config_from_real_file(tmp_path: Path):
    """Test loading from actual file."""
    # Arrange: Create real file
    config_file = tmp_path / "config.yaml"
    config_file.write_text("key: value\ncount: 42\n")

    # Act: Load from real file
    config = load_config(config_file)

    # Assert
    assert config["key"] == "value"
    assert config["count"] == 42

def test_save_and_load_task(tmp_path: Path):
    """Test full save/load cycle with real files."""
    repo = FileTaskRepository(tmp_path)
    task = Task(id="1", title="Test")

    # Save to real file
    repo.save(task)

    # Load from real file
    loaded = repo.get("1")

    assert loaded is not None
    assert loaded.id == task.id
    assert loaded.title == task.title
```

### Database Tests

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

@pytest.fixture
def db_session(tmp_path: Path):
    """Create real SQLite database for testing."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

def test_create_user_in_database(db_session: Session):
    """Test creating user in real database."""
    user = User(name="Test", email="test@example.com")
    db_session.add(user)
    db_session.commit()

    # Query real database
    found = db_session.query(User).filter_by(email="test@example.com").first()
    assert found is not None
    assert found.name == "Test"
```

### HTTP API Tests

```python
import pytest
import httpx
from fastapi.testclient import TestClient

@pytest.fixture
def client(app):
    """Create test client for real FastAPI app."""
    return TestClient(app)

def test_create_item_via_api(client: TestClient):
    """Test API endpoint with real HTTP request."""
    response = client.post(
        "/items",
        json={"name": "Test Item", "price": 10.0}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Item"

    # Verify persisted
    get_response = client.get(f"/items/{data['id']}")
    assert get_response.status_code == 200
```

---

## Parametrized Tests

### Basic Parametrization

```python
@pytest.mark.parametrize("input_val,expected", [
    ("hello", "HELLO"),
    ("World", "WORLD"),
    ("", ""),
    ("123", "123"),
])
def test_uppercase(input_val: str, expected: str):
    assert uppercase(input_val) == expected
```

### Multiple Parameters

```python
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
    (100, 200, 300),
])
def test_add(a: int, b: int, expected: int):
    assert add(a, b) == expected
```

### Edge Cases

```python
@pytest.mark.parametrize("invalid_input", [
    None,
    "",
    "   ",
    "\n\t",
])
def test_validate_rejects_invalid_input(invalid_input):
    with pytest.raises(ValidationError):
        validate(invalid_input)
```

---

## Exception Testing

### Basic Exception Testing

```python
def test_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        validate("")

    assert exc_info.value.field == "input"
    assert "required" in str(exc_info.value)

def test_raises_not_found_error():
    repo = TaskRepository()

    with pytest.raises(NotFoundError) as exc_info:
        repo.get("nonexistent")

    assert exc_info.value.entity_id == "nonexistent"
```

### Exception Message Matching

```python
def test_error_message():
    with pytest.raises(ValueError, match="must be positive"):
        set_count(-1)
```

---

## Async Testing

### pytest-asyncio

```python
import pytest

@pytest.mark.asyncio
async def test_async_fetch():
    result = await fetch_data("key")
    assert result is not None

@pytest.mark.asyncio
async def test_async_with_fixture(async_client):
    response = await async_client.get("/items")
    assert response.status_code == 200
```

### Async Fixtures

```python
@pytest.fixture
async def async_db():
    """Async database fixture."""
    db = await create_async_database()
    yield db
    await db.close()

@pytest.mark.asyncio
async def test_with_async_db(async_db):
    result = await async_db.query("SELECT 1")
    assert result == 1
```

---

## Test Markers

### Built-in Markers

```python
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    ...

@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix-only test"
)
def test_unix_permissions():
    ...

@pytest.mark.xfail(reason="Known bug #123")
def test_known_issue():
    ...
```

### Custom Markers

```python
# conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")

# test_*.py
@pytest.mark.slow
def test_large_file_processing():
    ...

@pytest.mark.integration
def test_database_connection():
    ...

# Run only fast tests
# pytest -m "not slow"

# Run only integration tests
# pytest -m integration
```

---

## Coverage

### Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = ["*/tests/*", "*/__init__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
fail_under = 80
show_missing = true
```

### Running with Coverage

```bash
# Run with coverage
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80
```

---

## TDD Workflow

### Step 1: Write Failing Test (RED)

```python
def test_calculate_total():
    """Test total calculation with discount."""
    items = [
        Item(price=100),
        Item(price=50),
    ]
    discount = 0.1  # 10%

    total = calculate_total(items, discount)

    assert total == 135.0  # (100 + 50) * 0.9
```

```bash
pytest tests/unit/test_calculator.py::test_calculate_total -v
# FAILED - calculate_total not implemented
```

### Step 2: Implement (GREEN)

```python
def calculate_total(items: list[Item], discount: float) -> float:
    subtotal = sum(item.price for item in items)
    return subtotal * (1 - discount)
```

```bash
pytest tests/unit/test_calculator.py::test_calculate_total -v
# PASSED
```

### Step 3: Refactor

```python
def calculate_total(
    items: Sequence[Item],
    discount: float = 0.0,
) -> float:
    """Calculate total with optional discount.

    Args:
        items: Items to sum
        discount: Discount percentage (0.0 to 1.0)

    Returns:
        Total after discount
    """
    if not 0 <= discount <= 1:
        raise ValueError("Discount must be between 0 and 1")

    subtotal = sum(item.price for item in items)
    return subtotal * (1 - discount)
```

```bash
pytest tests/unit/test_calculator.py -v
# All tests PASSED
mypy --strict src/calculator.py
# Success
```

---

## Anti-Patterns

### DO NOT:

```python
# DON'T use mocks
from unittest.mock import Mock, patch
@patch("module.function")  # BAD

# DON'T skip tests without reason
@pytest.mark.skip  # BAD - no reason

# DON'T use sleep for timing
import time
time.sleep(1)  # BAD - flaky

# DON'T test implementation details
assert service._private_method()  # BAD

# DON'T leave focused tests
def test_only_this():  # Rename from test_... to skip
    ...
```

### DO:

```python
# DO test real behavior
def test_save_load_cycle(tmp_path):
    repo.save(tmp_path, data)
    loaded = repo.load(tmp_path)
    assert loaded == data

# DO use fixtures for setup
@pytest.fixture
def configured_service(tmp_path):
    return Service(config_dir=tmp_path)

# DO test edge cases
@pytest.mark.parametrize("edge_case", [...])
def test_handles_edge_cases(edge_case):
    ...

# DO use pytest.raises for exceptions
with pytest.raises(ValueError):
    invalid_operation()
```

---

## Summary

1. **NO MOCKS** - Test real behavior always
2. Use fixtures for setup and teardown
3. Use tmp_path for file system tests
4. Use real databases (SQLite) for DB tests
5. Use TestClient for API tests
6. Parametrize edge cases
7. Follow TDD: RED -> GREEN -> REFACTOR
8. Aim for high coverage (80%+)
9. Mark slow tests appropriately
10. Keep tests fast and isolated
