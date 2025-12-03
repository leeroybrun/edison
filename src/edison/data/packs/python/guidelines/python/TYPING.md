# Python Type Hints Guide

Comprehensive guide for Python type annotations with mypy strict mode.

---

## Setup

### Enable Future Annotations

Always start files with:

```python
from __future__ import annotations
```

This enables postponed evaluation of annotations (PEP 563), allowing forward references without quotes.

### mypy Configuration

In `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_configs = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

---

## Basic Type Annotations

### Function Signatures

```python
def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"

def process(
    items: list[str],
    *,  # Keyword-only after this
    limit: int = 10,
    reverse: bool = False,
) -> list[str]:
    """Process items with options."""
    result = items[:limit]
    if reverse:
        result = result[::-1]
    return result
```

### Variables

```python
# Type inference works for simple cases
count = 0  # inferred as int
name = "test"  # inferred as str

# Explicit annotation when inference isn't clear
items: list[str] = []
config: dict[str, int] = {}
maybe_value: str | None = None
```

---

## Modern Type Syntax (Python 3.10+)

### Union Types

```python
# GOOD: Modern syntax
def get_value(key: str) -> str | None:
    return cache.get(key)

def process(data: str | bytes | Path) -> str:
    if isinstance(data, bytes):
        return data.decode()
    if isinstance(data, Path):
        return data.read_text()
    return data

# BAD: Legacy syntax
from typing import Optional, Union
def get_value(key: str) -> Optional[str]: ...
def process(data: Union[str, bytes, Path]) -> str: ...
```

### Built-in Generics

```python
# GOOD: Built-in generic syntax
def process(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

def get_mapping() -> dict[str, list[int]]:
    return {"values": [1, 2, 3]}

# BAD: typing module generics
from typing import List, Dict
def process(items: List[str]) -> Dict[str, int]: ...
```

---

## Generic Types

### TypeVar

```python
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T | None:
    """Return first item or None if empty."""
    return items[0] if items else None

# With bounds
from dataclasses import dataclass

@dataclass
class Entity:
    id: str

EntityT = TypeVar("EntityT", bound=Entity)

def get_by_id(entities: list[EntityT], id: str) -> EntityT | None:
    """Find entity by ID."""
    for entity in entities:
        if entity.id == id:
            return entity
    return None
```

### Generic Classes

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Repository(Generic[T]):
    """Generic repository for any entity type."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def get(self, id: str) -> T | None:
        return self._items.get(id)

    def save(self, id: str, item: T) -> None:
        self._items[id] = item

    def all(self) -> list[T]:
        return list(self._items.values())

# Usage
class Task:
    id: str
    title: str

task_repo: Repository[Task] = Repository()
task_repo.save("1", Task())
task: Task | None = task_repo.get("1")
```

---

## Protocol (Structural Typing)

### Define Protocols

```python
from typing import Protocol, runtime_checkable

class Serializable(Protocol):
    """Protocol for objects that can be serialized."""

    def to_dict(self) -> dict[str, Any]: ...

@runtime_checkable
class Identifiable(Protocol):
    """Protocol for objects with an ID."""

    @property
    def id(self) -> str: ...

# Any class with matching methods satisfies the protocol
class Task:
    def __init__(self, id: str) -> None:
        self._id = id

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id}

def serialize(obj: Serializable) -> str:
    return json.dumps(obj.to_dict())

# Works because Task has to_dict method
serialize(Task("123"))
```

### Protocol with Generic

```python
from typing import Protocol, TypeVar

T = TypeVar("T", covariant=True)

class Reader(Protocol[T]):
    def read(self) -> T: ...

class StringReader:
    def read(self) -> str:
        return "content"

def process_reader(reader: Reader[str]) -> str:
    return reader.read()

process_reader(StringReader())  # Works!
```

---

## Callable Types

### Function Types

```python
from collections.abc import Callable

def apply(
    func: Callable[[int, int], int],
    a: int,
    b: int,
) -> int:
    """Apply function to arguments."""
    return func(a, b)

# With variable arguments
def apply_all(
    func: Callable[..., int],
    *args: int,
) -> int:
    return func(*args)
```

### ParamSpec for Decorators

```python
from typing import ParamSpec, TypeVar
from collections.abc import Callable
from functools import wraps

P = ParamSpec("P")
R = TypeVar("R")

def logged(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that logs function calls."""
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Returned {result}")
        return result
    return wrapper

@logged
def add(a: int, b: int) -> int:
    return a + b

# Type checking preserved!
add(1, 2)  # OK
add("1", "2")  # Error: expected int
```

---

## Collection Types

### Iterable vs Sequence vs List

```python
from collections.abc import Iterable, Sequence

# Use Iterable for input (most flexible)
def process(items: Iterable[str]) -> None:
    for item in items:
        print(item)

# Use Sequence for indexed access
def get_first(items: Sequence[str]) -> str:
    return items[0]

# Use list for output (concrete type)
def create_items() -> list[str]:
    return ["a", "b", "c"]
```

### Mapping Types

```python
from collections.abc import Mapping, MutableMapping

# Use Mapping for read-only input
def get_value(config: Mapping[str, str], key: str) -> str:
    return config.get(key, "")

# Use MutableMapping if mutation needed
def set_value(config: MutableMapping[str, str], key: str, value: str) -> None:
    config[key] = value

# Use dict for concrete output
def create_config() -> dict[str, str]:
    return {"key": "value"}
```

---

## Special Types

### Any (Use Sparingly)

```python
from typing import Any

# Only use when truly dynamic
def handle_json(data: Any) -> None:
    # JSON can be any type
    if isinstance(data, dict):
        process_dict(data)
    elif isinstance(data, list):
        process_list(data)

# Prefer type narrowing instead
def handle_json_better(data: dict[str, Any] | list[Any] | str | int | float | bool | None) -> None:
    ...
```

### TypeAlias

```python
from typing import TypeAlias

# Define type aliases for complex types
JsonValue: TypeAlias = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None
ConfigDict: TypeAlias = dict[str, str | int | bool]

def load_json(path: Path) -> JsonValue:
    with open(path) as f:
        return json.load(f)
```

### Literal

```python
from typing import Literal

def set_log_level(level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]) -> None:
    ...

# Only these values allowed
set_log_level("DEBUG")  # OK
set_log_level("TRACE")  # Error!
```

### Final

```python
from typing import Final

MAX_RETRIES: Final = 3
API_VERSION: Final[str] = "v1"

# Cannot be reassigned
MAX_RETRIES = 5  # Error!
```

---

## Type Guards

### isinstance Narrowing

```python
def process(value: str | int) -> str:
    if isinstance(value, str):
        # Type is narrowed to str here
        return value.upper()
    else:
        # Type is narrowed to int here
        return str(value)
```

### TypeGuard

```python
from typing import TypeGuard

def is_string_list(items: list[object]) -> TypeGuard[list[str]]:
    """Check if all items are strings."""
    return all(isinstance(item, str) for item in items)

def process(items: list[object]) -> None:
    if is_string_list(items):
        # Type is narrowed to list[str]
        for item in items:
            print(item.upper())  # OK, item is str
```

---

## Overloads

```python
from typing import overload

@overload
def get_item(items: list[str], index: int) -> str: ...
@overload
def get_item(items: list[str], index: slice) -> list[str]: ...

def get_item(items: list[str], index: int | slice) -> str | list[str]:
    return items[index]

# Type checker knows return type based on input
item: str = get_item(["a", "b"], 0)
items: list[str] = get_item(["a", "b"], slice(0, 2))
```

---

## Common Patterns

### Optional vs Default

```python
# When None is a valid value
def find(key: str) -> str | None:
    return cache.get(key)  # Returns None if not found

# When there's a default
def get(key: str, default: str = "") -> str:
    return cache.get(key, default)

# Don't use Optional with default
# BAD
def bad(value: str | None = None) -> str:
    return value or "default"  # Confusing!

# GOOD
def good(value: str = "default") -> str:
    return value
```

### Self Type

```python
from typing import Self

class Builder:
    def __init__(self) -> None:
        self._name: str = ""

    def with_name(self, name: str) -> Self:
        self._name = name
        return self

    def build(self) -> "Result":
        return Result(self._name)

# Chaining works with correct types
builder = Builder().with_name("test")
```

---

## Type Ignore Comments

Only use when absolutely necessary, with explanation:

```python
# Third-party library without stubs
import untyped_lib  # type: ignore[import-untyped]

# Known issue that can't be fixed
result = legacy_api()  # type: ignore[no-any-return]  # Returns Any, wrapper pending

# NEVER do this
result = something()  # type: ignore  # BAD: No explanation
```

---

## Summary

1. Use `from __future__ import annotations`
2. Use modern syntax: `list[T]`, `dict[K, V]`, `T | None`
3. Run `mypy --strict` on all code
4. Use Protocol for duck typing
5. Use TypeVar for generic functions
6. Use ParamSpec for decorator types
7. Minimize `Any` usage
8. Document all `type: ignore` comments
