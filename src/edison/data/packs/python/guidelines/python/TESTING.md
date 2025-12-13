# Python Testing Guide

Comprehensive guide for pytest-based testing. For NO MOCKS policy, see the agent constitution.

---

<!-- section: pytest-config -->
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
<!-- /section: pytest-config -->

---

<!-- section: test-organization -->
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
<!-- /section: test-organization -->

---

<!-- section: fixtures -->
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
<!-- /section: fixtures -->

---

<!-- section: pytest-patterns -->
## Testing Patterns

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
<!-- /section: pytest-patterns -->

---

<!-- section: parametrize -->
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
<!-- /section: parametrize -->

---

<!-- section: async-testing -->
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
<!-- /section: async-testing -->

---

<!-- section: markers -->
## Test Markers

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
<!-- /section: markers -->

---

<!-- section: coverage -->
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
<!-- /section: coverage -->

---

## Summary

1. Use fixtures for setup and teardown
2. Use tmp_path for file system tests
3. Use real databases (SQLite) for DB tests
4. Use TestClient for API tests
5. Parametrize edge cases
6. Follow TDD: RED -> GREEN -> REFACTOR
7. Aim for high coverage (80%+)
8. Mark slow tests appropriately
9. Keep tests fast and isolated
