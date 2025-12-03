# Python Best Practices Guide

This guide defines Python development standards for Edison-managed projects.

---

## Modern Python (3.12+)

### Use Modern Type Syntax

```python
# GOOD: Modern syntax (Python 3.10+)
def process(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

def maybe_get(key: str) -> str | None:
    return cache.get(key)

# BAD: Legacy syntax
from typing import List, Dict, Optional
def process(items: List[str]) -> Dict[str, int]: ...
def maybe_get(key: str) -> Optional[str]: ...
```

### Use Dataclasses for Data Structures

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True, slots=True)
class Task:
    """Immutable task entity."""
    id: str
    title: str
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)

# Use frozen=True for immutability
# Use slots=True for memory efficiency
```

### Use Enums for Constants

```python
from enum import Enum, auto

class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

# Usage
task.status = TaskStatus.PENDING
if task.status == TaskStatus.COMPLETED:
    ...
```

### Use Protocol for Duck Typing

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Repository(Protocol[T]):
    """Repository interface for any entity type."""

    def get(self, id: str) -> T | None: ...
    def save(self, entity: T) -> None: ...
    def delete(self, id: str) -> bool: ...

# Any class implementing these methods satisfies the protocol
class TaskRepository:
    def get(self, id: str) -> Task | None: ...
    def save(self, entity: Task) -> None: ...
    def delete(self, id: str) -> bool: ...
```

### Use Match Statements

```python
def handle_event(event: Event) -> str:
    match event:
        case ClickEvent(x=x, y=y):
            return f"Clicked at ({x}, {y})"
        case KeyEvent(key="Enter"):
            return "Enter pressed"
        case KeyEvent(key=key):
            return f"Key pressed: {key}"
        case _:
            return "Unknown event"
```

---

## File and Path Handling

### Use pathlib.Path

```python
from pathlib import Path

# GOOD: pathlib
config_dir = Path.home() / ".config" / "app"
config_file = config_dir / "settings.yaml"

if config_file.exists():
    content = config_file.read_text()

# Create directories
config_dir.mkdir(parents=True, exist_ok=True)

# BAD: os.path
import os
config_dir = os.path.join(os.path.expanduser("~"), ".config", "app")
```

### Use Context Managers for Files

```python
# GOOD: Context manager
with open(path, "r") as f:
    content = f.read()

# Or with pathlib (even better)
content = Path(path).read_text()

# BAD: Manual file handling
f = open(path, "r")
content = f.read()
f.close()  # Might not be called on exception
```

---

## Error Handling

### Create Domain Exceptions

```python
class DomainError(Exception):
    """Base exception for all domain errors."""
    pass

class ValidationError(DomainError):
    """Raised when input validation fails."""
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

class NotFoundError(DomainError):
    """Raised when entity is not found."""
    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} not found: {entity_id}")
```

### Handle Exceptions Properly

```python
# GOOD: Specific exception handling
try:
    result = process(data)
except ValidationError as e:
    logger.warning(f"Validation failed: {e.field} - {e.message}")
    raise
except NotFoundError as e:
    logger.error(f"Entity not found: {e.entity_id}")
    return None

# BAD: Bare except
try:
    result = process(data)
except:  # Never do this
    pass

# BAD: Catching Exception without re-raise
try:
    result = process(data)
except Exception as e:
    print(e)  # Swallows all errors
```

---

## Code Organization

### Module Structure

```
src/
  package_name/
    __init__.py           # Public API only
    py.typed              # PEP 561 marker for type hints

    core/                 # Core business logic
      __init__.py
      models.py          # Data models (dataclasses)
      services.py        # Business logic (stateless)
      errors.py          # Domain exceptions

    adapters/            # External integrations
      __init__.py
      database.py        # Database adapter
      api.py             # External API adapter

    cli/                 # Command-line interface
      __init__.py
      main.py            # Entry point
      commands/          # Subcommands

    utils/               # Shared utilities
      __init__.py
      paths.py
      text.py
```

### Import Organization

```python
# Standard library
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

# Third-party
import yaml
from pydantic import BaseModel

# Local
from .core.models import Task
from .core.services import TaskService
from .utils.paths import resolve_path
```

---

## Configuration

### Load from YAML (No Hardcoding)

```python
from pathlib import Path
import yaml

def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path) as f:
        return yaml.safe_load(f)

# GOOD: Config from file
config = load_config(Path("config/settings.yaml"))
timeout = config["timeouts"]["default"]

# BAD: Hardcoded values
timeout = 30  # Magic number!
api_url = "https://api.example.com"  # Hardcoded URL!
```

### Use Environment Variables for Secrets Only

```python
import os
from pathlib import Path

def get_secret(name: str) -> str:
    """Get secret from environment variable."""
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

# Usage
api_key = get_secret("API_KEY")

# Never put secrets in code or config files
```

---

## Logging

### Use Structured Logging

```python
import logging
from typing import Any

logger = logging.getLogger(__name__)

def process_task(task_id: str, data: dict[str, Any]) -> None:
    logger.info("Processing task", extra={"task_id": task_id})

    try:
        result = do_work(data)
        logger.info(
            "Task completed",
            extra={"task_id": task_id, "result_size": len(result)}
        )
    except Exception as e:
        logger.exception(
            "Task failed",
            extra={"task_id": task_id, "error": str(e)}
        )
        raise
```

---

## Performance

### Use Generators for Large Data

```python
from collections.abc import Iterator
from pathlib import Path

def read_lines(path: Path) -> Iterator[str]:
    """Yield lines one at a time (memory efficient)."""
    with open(path) as f:
        for line in f:
            yield line.strip()

# Usage
for line in read_lines(large_file):
    process(line)
```

### Use functools for Caching

```python
from functools import cache, lru_cache

@cache  # Unlimited cache (use for small result sets)
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

@lru_cache(maxsize=100)  # Limited cache
def expensive_lookup(key: str) -> dict:
    return fetch_from_database(key)
```

---

## Anti-Patterns to Avoid

### DO NOT:

```python
# Don't use mutable default arguments
def bad(items: list = []):  # BAD
    items.append(1)
    return items

def good(items: list | None = None) -> list:  # GOOD
    if items is None:
        items = []
    items.append(1)
    return items

# Don't use global state
_cache = {}  # BAD: Global mutable state

# Don't ignore type errors
result: Any = get_value()  # BAD: Defeats type checking

# Don't use string formatting for SQL
query = f"SELECT * FROM users WHERE id = {user_id}"  # BAD: SQL injection

# Don't hardcode values
TIMEOUT = 30  # BAD if this should be configurable
```

---

## Summary

1. **Modern syntax**: Use Python 3.12+ features
2. **Strong typing**: mypy --strict must pass
3. **Dataclasses**: For data structures
4. **Protocols**: For duck typing
5. **pathlib**: For file paths
6. **Context managers**: For resources
7. **YAML config**: No hardcoded values
8. **Env vars**: For secrets only
9. **Structured logging**: For observability
10. **No mocks**: Test real behavior
