# Typing (mypy --strict)

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- All public functions must be annotated (params + return).
- Prefer `Protocol` for boundaries; avoid `Any`.
- Keep `# type: ignore[...]` rare and always justified.

### Minimal `pyproject.toml`

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_return_any = true
```

```py
from __future__ import annotations

from typing import Protocol

class Repo(Protocol):
    def get(self, id: str) -> str | None: ...
```
<!-- /section: patterns -->