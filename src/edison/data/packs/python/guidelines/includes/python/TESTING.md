# Testing (pytest)

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Use `tmp_path` for real filesystem tests.
- Use real databases for integration tests (SQLite is fine).
- Prefer fixtures for setup/teardown; parametrize edge cases.

```py
from pathlib import Path

def test_load_config(tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text("key: value\n")

    cfg = load_config(p)

    assert cfg["key"] == "value"
```

```py
import pytest

@pytest.mark.parametrize(
    "raw,ok",
    [("x", True), ("", False)],
)
def test_validate(raw: str, ok: bool):
    assert validate(raw) is ok
```
<!-- /section: patterns -->
