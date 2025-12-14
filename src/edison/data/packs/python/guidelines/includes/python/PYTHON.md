# Python (Modern)

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Target **Python 3.12+**.
- Prefer modern typing syntax: `list[T]`, `dict[str, T]`, `T | None`.
- Use `pathlib.Path` for filesystem paths.
- Use `@dataclass(frozen=True, slots=True)` for data objects.

```py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class Task:
    id: str
    title: str

CONFIG_DIR = Path.home() / ".config" / "app"
```

### Minimal project layout

```
src/
  package_name/
    __init__.py
    py.typed
    core/
    cli/
tests/
  unit/
  integration/
```
<!-- /section: patterns -->
