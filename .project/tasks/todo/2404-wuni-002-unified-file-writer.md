<!-- TaskID: 2404-wuni-002-unified-file-writer -->
<!-- Priority: 2404 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: refactor -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: codex -->
<!-- ParallelGroup: wave5-sequential -->
<!-- EstimatedHours: 4 -->
<!-- DependsOn: 2402-wtpl-002 -->
<!-- BlocksTask: none -->

# WUNI-002: Create Unified CompositionFileWriter Service

## Summary
Create a centralized `CompositionFileWriter` service that replaces scattered file writing patterns across registries, IDE composers, and adapters. This ensures consistent file I/O with proper directory creation, atomic writes, and auditing.

## Problem Statement

### Current Scattered File Writing
File writing is duplicated across ~15 files with nearly identical patterns:

**Pattern found everywhere:**
```python
ensure_directory(path.parent)
path.write_text(content, encoding="utf-8")
```

**JSON writing variant:**
```python
ensure_directory(path.parent)
write_json_atomic(path, data, indent=2)
```

### Affected Domains

| Domain | Files | Write Patterns |
|--------|-------|----------------|
| Registries | constitutions.py, rosters.py | ensure_dir + write_text |
| IDE Composers | hooks.py, commands.py, settings.py | ensure_dir + write_text + chmod |
| Adapters | claude.py, cursor.py, zen/sync.py | ensure_dir + write_text |
| Output | state_machine.py | ensure_dir + write_text |

### Issues
1. **No unified auditing** - Can't track all written files
2. **Inconsistent atomicity** - Some use atomic writes, some don't
3. **Duplicated ensure_directory calls** - Every write site repeats this
4. **No centralized error handling** - Each site handles errors differently
5. **Hooks need chmod** - Only HookComposer remembers to set executable bit

## Objectives
- [ ] Create `CompositionFileWriter` class
- [ ] Provide `write_text()`, `write_yaml()`, `write_json()` methods
- [ ] Handle directory creation automatically
- [ ] Support atomic writes
- [ ] Track all written files for reporting
- [ ] Support executable mode for hooks
- [ ] Replace all scattered write patterns

## Proposed Design

### CompositionFileWriter Class

```python
"""Unified file writing for Edison composition."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.io import ensure_directory, write_text_locked, write_json_atomic


@dataclass
class WriteResult:
    """Result of a write operation."""
    path: Path
    success: bool
    bytes_written: int = 0
    error: Optional[str] = None


class CompositionFileWriter:
    """Unified file writer for all composition output.

    Provides:
    - Automatic directory creation
    - Atomic writes (optional)
    - File tracking for reporting
    - Executable mode support
    - Consistent error handling

    Usage:
        writer = CompositionFileWriter()
        writer.write_text(path, content)
        writer.write_json(path, data)
        writer.write_executable(path, content)  # For hooks

        # Get summary
        print(f"Wrote {len(writer.files_written)} files")
    """

    def __init__(self, atomic: bool = False) -> None:
        """Initialize writer.

        Args:
            atomic: Whether to use atomic writes by default
        """
        self.atomic = atomic
        self.files_written: List[Path] = []
        self.errors: List[WriteResult] = []

    def write_text(
        self,
        path: Path,
        content: str,
        *,
        atomic: Optional[bool] = None,
        encoding: str = "utf-8",
    ) -> WriteResult:
        """Write text content to file.

        Args:
            path: Output file path
            content: Text content to write
            atomic: Override default atomic setting
            encoding: Text encoding (default: utf-8)

        Returns:
            WriteResult with success status
        """
        try:
            ensure_directory(path.parent)
            use_atomic = atomic if atomic is not None else self.atomic

            if use_atomic:
                write_text_locked(path, content)
            else:
                path.write_text(content, encoding=encoding)

            result = WriteResult(
                path=path,
                success=True,
                bytes_written=len(content.encode(encoding)),
            )
            self.files_written.append(path)
            return result

        except Exception as e:
            result = WriteResult(path=path, success=False, error=str(e))
            self.errors.append(result)
            return result

    def write_json(
        self,
        path: Path,
        data: Dict[str, Any],
        *,
        indent: int = 2,
        atomic: bool = True,
    ) -> WriteResult:
        """Write JSON data to file.

        Args:
            path: Output file path
            data: Dictionary to serialize
            indent: JSON indentation
            atomic: Use atomic write (default: True for JSON)

        Returns:
            WriteResult with success status
        """
        try:
            ensure_directory(path.parent)

            if atomic:
                write_json_atomic(path, data, indent=indent)
            else:
                import json
                path.write_text(json.dumps(data, indent=indent), encoding="utf-8")

            result = WriteResult(path=path, success=True)
            self.files_written.append(path)
            return result

        except Exception as e:
            result = WriteResult(path=path, success=False, error=str(e))
            self.errors.append(result)
            return result

    def write_yaml(
        self,
        path: Path,
        data: Dict[str, Any],
    ) -> WriteResult:
        """Write YAML data to file.

        Args:
            path: Output file path
            data: Dictionary to serialize

        Returns:
            WriteResult with success status
        """
        try:
            import yaml
            ensure_directory(path.parent)
            content = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
            path.write_text(content, encoding="utf-8")

            result = WriteResult(path=path, success=True, bytes_written=len(content))
            self.files_written.append(path)
            return result

        except Exception as e:
            result = WriteResult(path=path, success=False, error=str(e))
            self.errors.append(result)
            return result

    def write_executable(
        self,
        path: Path,
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> WriteResult:
        """Write executable script (for hooks).

        Sets executable bit after writing.

        Args:
            path: Output file path
            content: Script content
            encoding: Text encoding

        Returns:
            WriteResult with success status
        """
        result = self.write_text(path, content, encoding=encoding)
        if result.success:
            # Set executable bit
            path.chmod(path.stat().st_mode | 0o111)
        return result

    def reset(self) -> None:
        """Reset tracking for new composition run."""
        self.files_written.clear()
        self.errors.clear()

    def summary(self) -> Dict[str, Any]:
        """Get summary of all writes."""
        return {
            "files_written": len(self.files_written),
            "errors": len(self.errors),
            "paths": [str(p) for p in self.files_written],
            "error_details": [
                {"path": str(e.path), "error": e.error}
                for e in self.errors
            ],
        }
```

## Files to Create/Modify

### Create
```
src/edison/core/composition/core/writer.py   # CompositionFileWriter
tests/unit/composition/core/test_writer.py  # Tests
```

### Modify (replace scattered writes)
```
# Registries
src/edison/core/composition/registries/constitutions.py
src/edison/core/composition/registries/rosters.py
src/edison/core/composition/registries/rules.py
src/edison/core/composition/registries/schemas.py

# IDE Composers
src/edison/core/composition/ide/hooks.py
src/edison/core/composition/ide/commands.py
src/edison/core/composition/ide/settings.py

# Adapters
src/edison/core/adapters/sync/claude.py
src/edison/core/adapters/sync/cursor.py
src/edison/core/adapters/sync/zen/sync.py

# Output
src/edison/core/composition/output/state_machine.py
```

## Migration Pattern

### Before (scattered)
```python
# rosters.py
ensure_directory(output_path.parent)
output_path.write_text(content, encoding="utf-8")

# hooks.py
ensure_directory(out_path.parent)
out_path.write_text(rendered, encoding="utf-8")
out_path.chmod(out_path.stat().st_mode | 0o111)

# rules.py
ensure_directory(out_path.parent)
write_json_atomic(out_path, rules_data, indent=2)
```

### After (unified)
```python
# All files use writer
writer = CompositionFileWriter()

# rosters.py
writer.write_text(output_path, content)

# hooks.py
writer.write_executable(out_path, rendered)

# rules.py
writer.write_json(out_path, rules_data)
```

## Integration with CompositionPipeline

The `CompositionPipeline` from WTPL-002 should use `CompositionFileWriter` internally:

```python
class CompositionPipeline:
    def __init__(self, config: ConfigManager, project_root: Path):
        self._config = config
        self._project_root = project_root
        self._report = CompositionReport()
        self._writer = CompositionFileWriter(atomic=True)
        # ...

    def write(self, path: Path, content: str, content_type: str = "generic") -> None:
        processed = self.process(content, content_type)
        result = self._writer.write_text(path, processed)
        if result.success:
            self._report.record_file(path)
        else:
            self._report.add_error(f"Write failed: {result.error}")

    def write_json(self, path: Path, data: Dict) -> None:
        result = self._writer.write_json(path, data)
        if result.success:
            self._report.record_file(path)
        else:
            self._report.add_error(f"JSON write failed: {result.error}")

    def get_report(self) -> CompositionReport:
        # Include writer summary in report
        return self._report
```

## Verification Checklist
- [ ] CompositionFileWriter created with all methods
- [ ] write_text() handles atomic and non-atomic
- [ ] write_json() uses atomic by default
- [ ] write_executable() sets chmod
- [ ] All files_written tracked
- [ ] Errors captured and reported
- [ ] All scattered writes replaced
- [ ] Tests pass

## Success Criteria
1. Single `CompositionFileWriter` handles ALL file writes
2. No more scattered `ensure_directory()` + `write_text()` patterns
3. All written files tracked for reporting
4. Hooks get executable bit automatically
5. JSON files use atomic writes

## Related Files
- WTPL-002 implementation (uses this writer)
- All registry and IDE composer files
- All adapter sync files
