---
name: test-engineer
pack: python
overlay_type: extend
---

<!-- EXTEND: Tools -->

### Python Testing Tools

```bash
# Run all tests
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

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

<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->

### Python Testing Guidelines (NO MOCKS)

**CRITICAL**: Per CLAUDE.md, NO MOCKS EVER. Test real behavior.

1. **Use Real Files**
   ```python
   def test_load_config(tmp_path: Path):
       config_file = tmp_path / "config.yaml"
       config_file.write_text("key: value\n")

       config = load_config(config_file)

       assert config["key"] == "value"
   ```

2. **Use Real Database**
   ```python
   @pytest.fixture
   def db(tmp_path: Path):
       db_path = tmp_path / "test.db"
       engine = create_engine(f"sqlite:///{db_path}")
       yield Session(engine)

   def test_save_user(db: Session):
       user = User(name="Test")
       db.add(user)
       db.commit()

       found = db.query(User).first()
       assert found.name == "Test"
   ```

3. **Pytest Fixtures**
   ```python
   @pytest.fixture
   def task() -> Task:
       return Task(id="1", title="Test")

   @pytest.fixture
   def make_task():
       def _make(id: str = "1", **kwargs) -> Task:
           return Task(id=id, **kwargs)
       return _make
   ```

4. **Parametrize Edge Cases**
   ```python
   @pytest.mark.parametrize("input,expected", [
       ("valid", True),
       ("", False),
       (None, False),
   ])
   def test_validate(input, expected):
       assert validate(input) == expected
   ```

5. **Exception Testing**
   ```python
   def test_raises_on_invalid():
       with pytest.raises(ValidationError) as exc:
           validate("")
       assert exc.value.field == "input"
   ```

### Test File Organization

```
tests/
  conftest.py              # Shared fixtures
  unit/
    conftest.py            # Unit-specific fixtures
    test_models.py
    test_services.py
  integration/
    conftest.py
    test_database.py
  e2e/
    conftest.py
    test_workflow.py
  fixtures/
    sample_config.yaml
```

<!-- /EXTEND -->

<!-- SECTION: PytestPatterns -->

## Pytest Patterns

### Fixtures with Scope

```python
@pytest.fixture(scope="session")
def app_config():
    """Load config once per test session."""
    return load_config(Path("tests/fixtures/config.yaml"))

@pytest.fixture(scope="module")
def database(app_config):
    """Create database once per module."""
    db = create_database(app_config)
    yield db
    db.cleanup()

@pytest.fixture  # Default: function scope
def clean_task():
    """Fresh task for each test."""
    return Task(id="test-1")
```

### Async Testing

```python
import pytest

@pytest.mark.asyncio
async def test_async_fetch():
    result = await fetch_data("key")
    assert result is not None

@pytest.fixture
async def async_client():
    client = await create_client()
    yield client
    await client.close()
```

### Markers

```python
@pytest.mark.slow
def test_large_file():
    ...

@pytest.mark.integration
def test_database():
    ...

# Run: pytest -m "not slow"
```

<!-- /SECTION: PytestPatterns -->
