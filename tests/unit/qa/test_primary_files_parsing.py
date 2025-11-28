"""Test suite for primary files parsing utility.

This test ensures the consolidated parse_primary_files() function correctly
extracts file paths from task markdown content, handling various formats.
"""
from __future__ import annotations

import pytest


def test_parse_primary_files_extracts_bullet_list() -> None:
    """Should extract files from bulleted list under 'Primary Files / Areas' section."""
    from edison.core.qa._utils import parse_primary_files

    content = """# Task: Example

## Primary Files / Areas
- src/app/page.tsx
- src/components/Header.tsx
- lib/utils.ts

## Implementation Details
Some other content here.
"""

    result = parse_primary_files(content)
    assert result == [
        "src/app/page.tsx",
        "src/components/Header.tsx",
        "lib/utils.ts",
    ]


def test_parse_primary_files_handles_inline_format() -> None:
    """Should handle inline format: 'Primary Files / Areas: file1, file2'."""
    from edison.core.qa._utils import parse_primary_files

    content = """# Task: Example

Primary Files / Areas: src/main.ts, src/helper.ts

## Implementation
More content.
"""

    result = parse_primary_files(content)
    assert result == ["src/main.ts", "src/helper.ts"]


def test_parse_primary_files_handles_both_inline_and_bulleted() -> None:
    """Should extract files from both inline and bulleted formats."""
    from edison.core.qa._utils import parse_primary_files

    content = """# Task: Example

Primary Files / Areas: src/inline1.ts, src/inline2.ts
- src/bullet1.tsx
- src/bullet2.tsx

## Next Section
"""

    result = parse_primary_files(content)
    assert result == [
        "src/inline1.ts",
        "src/inline2.ts",
        "src/bullet1.tsx",
        "src/bullet2.tsx",
    ]


def test_parse_primary_files_alternative_header_format() -> None:
    """Should handle '- **Primary Files' markdown format."""
    from edison.core.qa._utils import parse_primary_files

    content = """# Task: Example

- **Primary Files / Areas**
- src/file1.ts
- src/file2.ts

## Implementation
"""

    result = parse_primary_files(content)
    assert result == ["src/file1.ts", "src/file2.ts"]


def test_parse_primary_files_stops_at_next_section() -> None:
    """Should stop extracting at the next section header."""
    from edison.core.qa._utils import parse_primary_files

    content = """# Task: Example

## Primary Files / Areas
- src/correct1.ts
- src/correct2.ts

## Implementation Details
- src/wrong1.ts
- src/wrong2.ts
"""

    result = parse_primary_files(content)
    assert result == ["src/correct1.ts", "src/correct2.ts"]


def test_parse_primary_files_empty_section() -> None:
    """Should return empty list when section exists but has no files."""
    from edison.core.qa._utils import parse_primary_files

    content = """# Task: Example

## Primary Files / Areas

## Implementation
"""

    result = parse_primary_files(content)
    assert result == []


def test_parse_primary_files_no_section() -> None:
    """Should return empty list when section doesn't exist."""
    from edison.core.qa._utils import parse_primary_files

    content = """# Task: Example

## Implementation
- src/file.ts
"""

    result = parse_primary_files(content)
    assert result == []


def test_parse_primary_files_handles_whitespace() -> None:
    """Should strip whitespace from extracted file paths."""
    from edison.core.qa._utils import parse_primary_files

    content = """# Task: Example

Primary Files / Areas:  src/file1.ts  ,  src/file2.ts
-   src/file3.ts
-  src/file4.ts

## Next
"""

    result = parse_primary_files(content)
    assert result == [
        "src/file1.ts",
        "src/file2.ts",
        "src/file3.ts",
        "src/file4.ts",
    ]


def test_parse_primary_files_ignores_errors() -> None:
    """Should handle malformed content gracefully."""
    from edison.core.qa._utils import parse_primary_files

    # Minimal valid content
    result = parse_primary_files("")
    assert result == []

    # Just a header
    result = parse_primary_files("## Primary Files / Areas")
    assert result == []
