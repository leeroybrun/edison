<!-- TaskID: 2402-wtpl-002-template-variable-impl -->
<!-- Priority: 2402 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: feature -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: codex -->
<!-- ParallelGroup: wave5-sequential -->
<!-- EstimatedHours: 12 -->
<!-- DependsOn: 2401-wtpl-001 -->
<!-- BlocksTask: none -->

# WTPL-002: Implement Unified CompositionPipeline

## Summary
Implement the `CompositionPipeline` class designed in WTPL-001. This creates a SINGLE entry point for ALL template processing in Edison, replacing the current 18 scattered write points with unified processing: includes → sections → config vars → legacy vars → validation → write.

## Prerequisites
- **MUST** complete WTPL-001 first (design specification)
- Understand existing infrastructure:
  - `ConfigManager` in `src/edison/core/config/manager.py`
  - `resolve_includes()` in `src/edison/core/composition/includes.py`
  - `SectionParser` in `src/edison/core/composition/core/sections.py`
  - `write_text_locked()` in `src/edison/core/utils/io/core.py`

## Problem Statement
Edison currently has 18 scattered write points and 5 different template mechanisms:
- Section-based (`{{SECTION:Name}}`) - Agents, Validators only
- Include system (`{{include:path}}`) - Manual calls
- Handlebars loops (`{{#each}}`) - Constitutions only
- Simple replace (`{{source_layers}}`) - Rosters only
- Jinja2 (`{{ var }}`) - Hooks only

This task implements the unified `CompositionPipeline` from WTPL-001 that:
1. Provides a SINGLE entry point for all template processing
2. Applies transformations in correct order automatically
3. Uses existing infrastructure (NO duplication)
4. Reports all unresolved variables across all files

## Objectives
- [ ] Create `CompositionPipeline` class in `core/composition/pipeline.py`
- [ ] Create `CompositionReport` class for unified reporting
- [ ] Migrate ALL 18 write points to use `pipeline.write()`
- [ ] Add validation for unresolved patterns
- [ ] Test end-to-end with comprehensive tests

## Architecture (from WTPL-001)

### Transformation Order (MUST be this order)
```
1. INCLUDES      {{include:path/to/file}}
   - Recursive resolution (max depth: 3)
   - Must happen FIRST (included content has variables)

2. SECTIONS      {{SECTION:Name}}, {{#each collection}}
   - Only for content types that use sections
   - Handled by existing SectionComposer

3. CONFIG VARS   {{config.project.name}}
   - Uses ConfigManager.get() for resolution
   - Tracks missing variables

4. LEGACY VARS   {{source_layers}}, {{timestamp}}, etc.
   - Metadata variables for provenance
   - Passed via context dict

5. VALIDATION    Check for unresolved {{...}} patterns
   - Warn on missing config vars
   - Track all unresolved for report

6. WRITE         Safe atomic write to disk
   - Uses write_text_locked() for safety
   - Creates parent directories
```

### Key Principle: USE EXISTING CODE
| Need | Existing Code | Location |
|------|---------------|----------|
| Config loading | `ConfigManager` | `core/config/manager.py` |
| Config access | `ConfigManager.get(path)` | `core/config/manager.py` |
| Deep merge | `deep_merge()` | `core/utils/merge.py` |
| Include resolution | `resolve_includes()` | `core/composition/includes.py` |
| Section parsing | `SectionParser` | `core/composition/core/sections.py` |
| Safe writes | `write_text_locked()` | `core/utils/io/core.py` |
| JSON writes | `write_json_atomic()` | `core/utils/io/json.py` |

## Source Files

### Files to Create
```
src/edison/core/composition/core/pipeline.py   # CompositionPipeline class (in core/)
src/edison/core/composition/core/report.py     # CompositionReport class (in core/)
tests/unit/composition/core/test_pipeline.py   # Comprehensive tests
```

**IMPORTANT: Pipeline is in `composition/core/` NOT top-level `composition/`**

Rationale:
1. `core/` is the foundation layer - pipeline uses these tools (sections, paths, composer)
2. Registries import from `core/` - clear dependency flow
3. Matches existing pattern (composer.py, sections.py, paths.py are in core/)
4. Avoids circular dependencies - core imports nothing from registries/ide/adapters

### Files to Modify (18 write points)
```
# CLI compose (5 write points)
src/edison/cli/compose/all.py              # Lines 185, 207, 226, 277, 289

# Registries (7 write points)
src/edison/core/composition/registries/constitutions.py  # Line 320
src/edison/core/composition/registries/rosters.py        # Lines 57, 121, 257
src/edison/core/composition/registries/rules.py          # Line 445
src/edison/core/composition/registries/schemas.py        # Line 116

# Output (1 write point)
src/edison/core/composition/output/state_machine.py      # Line 222

# IDE (3 write points)
src/edison/core/composition/ide/hooks.py                 # Line 107
src/edison/core/composition/ide/settings.py              # Line 160
src/edison/core/composition/ide/commands.py              # Line 189

# Includes cache (2 write points)
src/edison/core/composition/includes.py                  # Lines 221, 232
```

## Precise Instructions

### Step 1: Create CompositionReport Class

Create `src/edison/core/composition/core/report.py`:

```python
"""Unified composition reporting for Edison."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set


@dataclass
class CompositionReport:
    """Tracks all composition activity for unified reporting.

    This class aggregates information about all files processed,
    variables substituted, and any issues encountered during
    composition. It provides a single source of truth for
    composition status.
    """

    files_written: List[Path] = field(default_factory=list)
    variables_substituted: Set[str] = field(default_factory=set)
    variables_missing: Set[str] = field(default_factory=set)
    includes_resolved: Set[str] = field(default_factory=set)
    sections_processed: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def record_file(self, path: Path) -> None:
        """Record a file that was written."""
        self.files_written.append(path)

    def record_variable(self, var_path: str, resolved: bool) -> None:
        """Record a variable substitution attempt."""
        if resolved:
            self.variables_substituted.add(var_path)
        else:
            self.variables_missing.add(var_path)

    def record_include(self, include_path: str) -> None:
        """Record an include that was resolved."""
        self.includes_resolved.add(include_path)

    def record_section(self, section_name: str) -> None:
        """Record a section that was processed."""
        self.sections_processed.add(section_name)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def has_unresolved(self) -> bool:
        """Check if there are any unresolved variables."""
        return len(self.variables_missing) > 0

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def summary(self) -> str:
        """Generate a human-readable summary of composition activity."""
        lines = [
            f"Files written: {len(self.files_written)}",
            f"Variables substituted: {len(self.variables_substituted)}",
            f"Includes resolved: {len(self.includes_resolved)}",
            f"Sections processed: {len(self.sections_processed)}",
        ]

        if self.variables_missing:
            lines.append(f"Missing variables: {len(self.variables_missing)}")
            for var in sorted(self.variables_missing):
                lines.append(f"  - {{{{config.{var}}}}}")

        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
            for error in self.errors:
                lines.append(f"  - {error}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "files_written": [str(p) for p in self.files_written],
            "variables_substituted": sorted(self.variables_substituted),
            "variables_missing": sorted(self.variables_missing),
            "includes_resolved": sorted(self.includes_resolved),
            "sections_processed": sorted(self.sections_processed),
            "warnings": self.warnings,
            "errors": self.errors,
            "success": not self.has_errors(),
        }


__all__ = ["CompositionReport"]
```

### Step 2: Create CompositionPipeline Class

Create `src/edison/core/composition/core/pipeline.py`:

```python
"""Unified composition pipeline for all template processing.

This module provides the CompositionPipeline class which is the SINGLE
entry point for all template processing in Edison. It replaces 18
scattered write points with unified processing.

Transformation order:
1. INCLUDES - Resolve {{include:path}} directives
2. SECTIONS - Process {{SECTION:Name}} and {{#each}} blocks
3. CONFIG VARS - Substitute {{config.path}} variables
4. LEGACY VARS - Replace {{source_layers}}, {{timestamp}}, etc.
5. VALIDATION - Check for unresolved patterns
6. WRITE - Safe atomic write to disk
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from .report import CompositionReport

if TYPE_CHECKING:
    from edison.core.config import ConfigManager


class CompositionPipeline:
    """Unified composition pipeline for all template processing.

    This class provides a single entry point for processing templates
    and writing output files. It ensures consistent transformation
    order across ALL composers.

    Example:
        >>> from edison.core.config import ConfigManager
        >>> cfg = ConfigManager(repo_root)
        >>> pipeline = CompositionPipeline(cfg, repo_root)
        >>> pipeline.set_context(source_layers="core, project")
        >>> pipeline.write(output_path, content, "agent")
    """

    # Pattern definitions (order matters for non-overlap)
    INCLUDE_PATTERN = re.compile(r'\{\{include:([^}]+)\}\}')
    SECTION_PATTERN = re.compile(r'\{\{SECTION:([^}]+)\}\}')
    EACH_START_PATTERN = re.compile(r'\{\{#each\s+([^}]+)\}\}')
    EACH_END_PATTERN = re.compile(r'\{\{/each\}\}')
    CONFIG_PATTERN = re.compile(r'\{\{config\.([a-zA-Z_][a-zA-Z0-9_.]*)\}\}')
    LEGACY_PATTERN = re.compile(
        r'\{\{(source_layers|timestamp|version|template_name|PROJECT_EDISON_DIR)\}\}'
    )
    # Pattern to detect ANY unresolved {{...}} after processing
    UNRESOLVED_PATTERN = re.compile(r'\{\{[^}]+\}\}')

    # Content types that use section processing
    SECTION_CONTENT_TYPES = {"agent", "validator", "constitution"}

    def __init__(
        self,
        config: "ConfigManager",
        project_root: Path,
        max_include_depth: int = 3,
    ) -> None:
        """Initialize the composition pipeline.

        Args:
            config: ConfigManager instance with loaded configuration.
            project_root: Root directory of the project.
            max_include_depth: Maximum depth for recursive includes (default: 3).
        """
        self._config = config
        self._project_root = project_root
        self._max_include_depth = max_include_depth
        self._report = CompositionReport()
        self._context: Dict[str, Any] = {}

    def set_context(self, **kwargs: Any) -> None:
        """Set legacy context variables for substitution.

        Args:
            **kwargs: Variables like source_layers, timestamp, version, etc.
        """
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context variables."""
        self._context.clear()

    def process(
        self,
        content: str,
        content_type: str = "generic",
        section_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Apply all transformations in correct order.

        Args:
            content: Raw template content to process.
            content_type: Type of content (agent, validator, constitution, etc.).
            section_data: Optional data for section/Handlebars processing.

        Returns:
            Fully processed content with all substitutions applied.
        """
        # Step 1: Resolve includes
        content = self._resolve_includes(content, depth=0)

        # Step 2: Process sections (only for content types that use them)
        if content_type in self.SECTION_CONTENT_TYPES and section_data:
            content = self._process_sections(content, section_data)

        # Step 3: Substitute config variables
        content = self._substitute_config_vars(content)

        # Step 4: Substitute legacy variables
        content = self._substitute_legacy_vars(content)

        # Step 5: Validate for unresolved patterns
        self._validate_unresolved(content)

        return content

    def write(
        self,
        path: Path,
        content: str,
        content_type: str = "generic",
        section_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Process content and write to file.

        This is the main entry point for composers. It processes
        the content through all transformation stages and writes
        the result atomically to disk.

        Args:
            path: Output file path.
            content: Raw template content.
            content_type: Type of content for section processing.
            section_data: Optional data for section/Handlebars processing.
        """
        # Process content
        processed = self.process(content, content_type, section_data)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically using existing utility
        from edison.core.utils.io import write_text_locked
        write_text_locked(path, processed)

        # Record in report
        self._report.record_file(path)

    def write_json(
        self,
        path: Path,
        data: Dict[str, Any],
        indent: int = 2,
    ) -> None:
        """Write JSON data to file.

        For JSON files, no template processing is needed - just
        safe atomic write.

        Args:
            path: Output file path.
            data: Dictionary to serialize as JSON.
            indent: JSON indentation level (default: 2).
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically using existing utility
        from edison.core.utils.io import write_json_atomic
        write_json_atomic(path, data, indent=indent)

        # Record in report
        self._report.record_file(path)

    def get_report(self) -> CompositionReport:
        """Get the unified composition report.

        Returns:
            CompositionReport with all activity tracked.
        """
        return self._report

    def reset_report(self) -> None:
        """Reset the composition report for a new composition run."""
        self._report = CompositionReport()

    # --- Private transformation methods ---

    def _resolve_includes(self, content: str, depth: int) -> str:
        """Resolve {{include:path}} directives recursively.

        Uses existing resolve_includes() infrastructure.
        """
        if depth >= self._max_include_depth:
            self._report.add_warning(
                f"Max include depth ({self._max_include_depth}) reached"
            )
            return content

        def replacer(match: re.Match) -> str:
            include_path = match.group(1)
            self._report.record_include(include_path)

            # Use existing include resolution
            from edison.core.composition.includes import resolve_single_include
            try:
                included_content = resolve_single_include(
                    include_path, self._project_root, self._config
                )
                # Recursively resolve includes in the included content
                return self._resolve_includes(included_content, depth + 1)
            except FileNotFoundError as e:
                self._report.add_error(f"Include not found: {include_path}")
                return match.group(0)  # Leave unresolved

        return self.INCLUDE_PATTERN.sub(replacer, content)

    def _process_sections(
        self,
        content: str,
        section_data: Dict[str, Any],
    ) -> str:
        """Process {{SECTION:Name}} and {{#each}} blocks.

        Uses existing SectionParser infrastructure.
        """
        from edison.core.composition.core.sections import SectionParser

        parser = SectionParser()

        # Track processed sections
        for match in self.SECTION_PATTERN.finditer(content):
            self._report.record_section(match.group(1))

        # Process sections using existing parser
        return parser.process(content, section_data)

    def _substitute_config_vars(self, content: str) -> str:
        """Substitute {{config.path}} variables using ConfigManager."""

        def replacer(match: re.Match) -> str:
            var_path = match.group(1)
            value = self._config.get(var_path)

            if value is None:
                self._report.record_variable(var_path, resolved=False)
                return match.group(0)  # Leave unresolved

            self._report.record_variable(var_path, resolved=True)

            # Handle different value types
            if isinstance(value, (list, dict)):
                return json.dumps(value)
            return str(value)

        return self.CONFIG_PATTERN.sub(replacer, content)

    def _substitute_legacy_vars(self, content: str) -> str:
        """Substitute legacy variables from context."""

        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            value = self._context.get(var_name)

            if value is None:
                # Don't report as missing - legacy vars are optional
                return match.group(0)

            return str(value)

        return self.LEGACY_PATTERN.sub(replacer, content)

    def _validate_unresolved(self, content: str) -> None:
        """Check for any remaining unresolved patterns."""
        # Find all remaining {{...}} patterns
        unresolved = self.UNRESOLVED_PATTERN.findall(content)

        # Filter out known patterns that are intentionally unresolved
        known_patterns = {
            "{{SECTION:", "{{#each", "{{/each}}",
            "{{EXTENSIBLE_SECTIONS}}", "{{APPEND_SECTIONS}}",
        }

        for pattern in unresolved:
            if not any(pattern.startswith(k) for k in known_patterns):
                # Check if it's a config var we couldn't resolve
                config_match = self.CONFIG_PATTERN.match(pattern)
                if config_match:
                    # Already tracked in _substitute_config_vars
                    pass
                elif self.LEGACY_PATTERN.match(pattern):
                    # Legacy var without context - this is ok
                    pass
                else:
                    # Unknown pattern
                    self._report.add_warning(f"Unresolved pattern: {pattern}")


__all__ = ["CompositionPipeline"]
```

### Step 3: Create Helper for Single Include Resolution

Add to `src/edison/core/composition/includes.py`:

```python
def resolve_single_include(
    include_path: str,
    project_root: Path,
    config: "ConfigManager",
) -> str:
    """Resolve a single include path to its content.

    This function is used by CompositionPipeline for include resolution.
    It searches the three-layer hierarchy: core → packs → project.

    Args:
        include_path: Relative path from {{include:path}}
        project_root: Project root directory
        config: ConfigManager for pack resolution

    Returns:
        Content of the included file

    Raises:
        FileNotFoundError: If file not found in any layer
    """
    from edison.data import get_data_path

    # Search order: project → packs → core
    search_paths = []

    # 1. Project layer
    project_file = project_root / ".edison" / include_path
    search_paths.append(project_file)

    # 2. Pack layers (in reverse order for precedence)
    active_packs = config.get("packs.active", [])
    for pack in reversed(active_packs):
        pack_file = project_root / ".edison" / "packs" / pack / include_path
        search_paths.append(pack_file)

    # 3. Core layer (bundled data)
    core_file = get_data_path(include_path)
    search_paths.append(core_file)

    # Find first existing file
    for path in search_paths:
        if path.exists():
            return path.read_text(encoding="utf-8")

    raise FileNotFoundError(
        f"Include not found: {include_path}\n"
        f"Searched: {[str(p) for p in search_paths]}"
    )
```

### Step 4: Migrate Write Points to Pipeline

Each of the 18 write points needs to be migrated to use `pipeline.write()`. Here's the pattern:

**Before (scattered):**
```python
# In cli/compose/all.py
output_file.write_text(content, encoding="utf-8")
```

**After (unified):**
```python
# In cli/compose/all.py
pipeline.write(output_file, content, "agent")
```

**Full migration for `cli/compose/all.py`:**

```python
# At top of main()
from edison.core.composition.pipeline import CompositionPipeline

def main(args) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else find_project_root()
    cfg_mgr = ConfigManager(repo_root)

    # Create unified pipeline
    pipeline = CompositionPipeline(cfg_mgr, repo_root)
    pipeline.set_context(
        source_layers="core, packs, project",
        timestamp=datetime.now().isoformat(),
        version=__version__,
    )

    output_root = get_project_config_dir(repo_root) / "_generated"

    # ... existing logic ...

    # Replace all write_text() calls with pipeline.write()

    # Agents (was line 185)
    for agent_name, content in agent_contents.items():
        output_path = output_root / "agents" / f"{agent_name}.md"
        pipeline.write(output_path, content, "agent")

    # Guidelines (was line 207)
    for guideline_name, content in guideline_contents.items():
        output_path = output_root / "guidelines" / f"{guideline_name}.md"
        pipeline.write(output_path, content, "guideline")

    # Validators (was line 226)
    for validator_name, content in validator_contents.items():
        output_path = output_root / "validators" / f"{validator_name}.md"
        pipeline.write(output_path, content, "validator")

    # Start prompts (was lines 277, 289)
    for prompt_name, content in prompt_contents.items():
        output_path = output_root / "start" / f"{prompt_name}.md"
        pipeline.write(output_path, content, "start_prompt")

    # At end, show report
    report = pipeline.get_report()
    if report.has_unresolved():
        console.print(f"[yellow]{report.summary()}[/yellow]")

    return 0 if not report.has_errors() else 1
```

### Step 5: Migrate Registry Write Points

**constitutions.py (line 320):**
```python
def generate_all_constitutions(
    config: ConfigManager,
    output_root: Path,
    pipeline: Optional[CompositionPipeline] = None,
) -> None:
    if pipeline is None:
        pipeline = CompositionPipeline(config, config.project_root)

    # ... existing composition logic ...

    for role, content in composed_constitutions.items():
        output_path = output_root / "constitutions" / f"{role.upper()}.md"
        pipeline.write(output_path, content, "constitution", section_data=role_data)
```

**rosters.py (lines 57, 121, 257):**
```python
def generate_available_agents(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    content = _build_agents_roster(config)
    pipeline.write(output_root / "rosters" / "AGENTS.md", content, "roster")

def generate_available_validators(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    content = _build_validators_roster(config)
    pipeline.write(output_root / "rosters" / "VALIDATORS.md", content, "roster")

def generate_canonical_entry(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    content = _build_canonical_entry(config)
    pipeline.write(output_root / "CANONICAL_ENTRY.md", content, "roster")
```

**rules.py (line 445):**
```python
def generate_rules_json(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    rules_data = _collect_all_rules(config)
    pipeline.write_json(output_root / "rules" / "rules.json", rules_data)
```

**schemas.py (line 116):**
```python
def generate_json_schemas(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    schemas = _collect_all_schemas(config)
    for schema_name, schema_data in schemas.items():
        pipeline.write_json(
            output_root / "schemas" / f"{schema_name}.json",
            schema_data
        )
```

### Step 6: Migrate IDE Write Points

**hooks.py (line 107):**
```python
def compose_all_hooks(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    for hook_name, content in _render_all_hooks(config):
        output_path = output_root / "hooks" / f"{hook_name}.sh"
        pipeline.write(output_path, content, "hook")
```

**settings.py (line 160):**
```python
def generate_settings(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    settings_data = _build_settings(config)
    pipeline.write_json(output_root / "settings.json", settings_data)
```

**commands.py (line 189):**
```python
def compose_all_commands(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    for cmd_name, content in _render_all_commands(config):
        output_path = output_root / "commands" / f"{cmd_name}.md"
        pipeline.write(output_path, content, "command")
```

### Step 7: Migrate State Machine Write Point

**state_machine.py (line 222):**
```python
def generate_state_machine_doc(
    config: ConfigManager,
    output_root: Path,
    pipeline: CompositionPipeline,
) -> None:
    content = _build_state_machine_doc(config)
    pipeline.write(output_root / "STATE_MACHINE.md", content, "state_machine")
```

### Step 8: Create Comprehensive Tests

Create `tests/unit/composition/test_pipeline.py`:

```python
"""Tests for CompositionPipeline."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from edison.core.composition.pipeline import CompositionPipeline
from edison.core.composition.report import CompositionReport


class MockConfigManager:
    """Mock ConfigManager for testing."""

    def __init__(self, config: dict, project_root: Path):
        self._config = config
        self.project_root = project_root

    def get(self, path: str, default=None):
        """Get value by dot-notation path."""
        keys = path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value


class TestCompositionPipeline:
    """Tests for CompositionPipeline."""

    def test_process_simple_config_var(self, tmp_path: Path):
        """Test substituting a simple config variable."""
        config = MockConfigManager(
            {"project": {"name": "test-project"}},
            tmp_path
        )
        pipeline = CompositionPipeline(config, tmp_path)

        result = pipeline.process("Project: {{config.project.name}}")

        assert result == "Project: test-project"
        assert "project.name" in pipeline.get_report().variables_substituted

    def test_process_nested_config_var(self, tmp_path: Path):
        """Test substituting a nested config variable."""
        config = MockConfigManager(
            {"project": {"database": {"tablePrefix": "dashboard_"}}},
            tmp_path
        )
        pipeline = CompositionPipeline(config, tmp_path)

        result = pipeline.process(
            "Tables: {{config.project.database.tablePrefix}}"
        )

        assert result == "Tables: dashboard_"

    def test_missing_config_var_unchanged(self, tmp_path: Path):
        """Test that missing config vars are left unchanged."""
        config = MockConfigManager({}, tmp_path)
        pipeline = CompositionPipeline(config, tmp_path)

        result = pipeline.process("{{config.nonexistent.var}}")

        assert result == "{{config.nonexistent.var}}"
        assert "nonexistent.var" in pipeline.get_report().variables_missing

    def test_legacy_var_substitution(self, tmp_path: Path):
        """Test legacy variable substitution from context."""
        config = MockConfigManager({}, tmp_path)
        pipeline = CompositionPipeline(config, tmp_path)
        pipeline.set_context(source_layers="core, project")

        result = pipeline.process("Src: {{source_layers}}")

        assert result == "Src: core, project"

    def test_does_not_touch_section_markers(self, tmp_path: Path):
        """Test that section markers are not processed as variables."""
        config = MockConfigManager({}, tmp_path)
        pipeline = CompositionPipeline(config, tmp_path)

        result = pipeline.process("{{SECTION:MySection}}", content_type="generic")

        # Section markers left alone in generic content
        assert "{{SECTION:MySection}}" in result

    def test_does_not_touch_handlebars_loops(self, tmp_path: Path):
        """Test that Handlebars loops are not touched."""
        config = MockConfigManager({}, tmp_path)
        pipeline = CompositionPipeline(config, tmp_path)

        result = pipeline.process("{{#each rules}}{{/each}}", content_type="generic")

        assert "{{#each rules}}" in result
        assert "{{/each}}" in result

    def test_transformation_order(self, tmp_path: Path):
        """Test that transformations happen in correct order."""
        # Create include file with config var
        include_dir = tmp_path / ".edison"
        include_dir.mkdir(parents=True)
        (include_dir / "included.md").write_text(
            "Included: {{config.project.name}}",
            encoding="utf-8"
        )

        config = MockConfigManager(
            {"project": {"name": "test"}},
            tmp_path
        )

        with patch(
            "edison.core.composition.pipeline.resolve_single_include"
        ) as mock_include:
            mock_include.return_value = "Included: {{config.project.name}}"

            pipeline = CompositionPipeline(config, tmp_path)
            result = pipeline.process("{{include:included.md}}")

            # Include should be resolved, then config var substituted
            assert result == "Included: test"

    def test_write_creates_directory(self, tmp_path: Path):
        """Test that write creates parent directories."""
        config = MockConfigManager({}, tmp_path)
        pipeline = CompositionPipeline(config, tmp_path)

        output_path = tmp_path / "nested" / "dir" / "file.md"

        with patch("edison.core.composition.pipeline.write_text_locked") as mock_write:
            pipeline.write(output_path, "content")

            assert output_path.parent.exists()
            mock_write.assert_called_once()

    def test_write_json(self, tmp_path: Path):
        """Test JSON file writing."""
        config = MockConfigManager({}, tmp_path)
        pipeline = CompositionPipeline(config, tmp_path)

        output_path = tmp_path / "data.json"

        with patch("edison.core.composition.pipeline.write_json_atomic") as mock_write:
            pipeline.write_json(output_path, {"key": "value"})

            mock_write.assert_called_once()

    def test_report_tracks_all_activity(self, tmp_path: Path):
        """Test that report tracks all composition activity."""
        config = MockConfigManager(
            {"project": {"name": "test"}},
            tmp_path
        )
        pipeline = CompositionPipeline(config, tmp_path)
        pipeline.set_context(source_layers="core")

        content = "{{config.project.name}} {{config.missing}} {{source_layers}}"
        pipeline.process(content)

        report = pipeline.get_report()
        assert "project.name" in report.variables_substituted
        assert "missing" in report.variables_missing
        assert report.has_unresolved()

    def test_reset_report(self, tmp_path: Path):
        """Test report reset between composition runs."""
        config = MockConfigManager(
            {"project": {"name": "test"}},
            tmp_path
        )
        pipeline = CompositionPipeline(config, tmp_path)

        pipeline.process("{{config.project.name}}")
        assert len(pipeline.get_report().variables_substituted) == 1

        pipeline.reset_report()
        assert len(pipeline.get_report().variables_substituted) == 0


class TestCompositionReport:
    """Tests for CompositionReport."""

    def test_record_file(self):
        """Test file recording."""
        report = CompositionReport()
        report.record_file(Path("/test/file.md"))

        assert len(report.files_written) == 1
        assert report.files_written[0] == Path("/test/file.md")

    def test_record_variable_resolved(self):
        """Test recording resolved variables."""
        report = CompositionReport()
        report.record_variable("project.name", resolved=True)

        assert "project.name" in report.variables_substituted
        assert "project.name" not in report.variables_missing

    def test_record_variable_missing(self):
        """Test recording missing variables."""
        report = CompositionReport()
        report.record_variable("project.name", resolved=False)

        assert "project.name" not in report.variables_substituted
        assert "project.name" in report.variables_missing

    def test_has_unresolved(self):
        """Test has_unresolved check."""
        report = CompositionReport()
        assert not report.has_unresolved()

        report.record_variable("missing", resolved=False)
        assert report.has_unresolved()

    def test_summary(self):
        """Test summary generation."""
        report = CompositionReport()
        report.record_file(Path("/test.md"))
        report.record_variable("found", resolved=True)
        report.record_variable("missing", resolved=False)
        report.add_warning("Test warning")

        summary = report.summary()

        assert "Files written: 1" in summary
        assert "Variables substituted: 1" in summary
        assert "Missing variables: 1" in summary
        assert "{{config.missing}}" in summary
        assert "Test warning" in summary

    def test_to_dict(self):
        """Test dict conversion for JSON serialization."""
        report = CompositionReport()
        report.record_file(Path("/test.md"))
        report.record_variable("var", resolved=True)

        d = report.to_dict()

        assert d["files_written"] == ["/test.md"]
        assert d["variables_substituted"] == ["var"]
        assert d["success"] is True
```

### Step 9: Update Module Exports

Update `src/edison/core/composition/core/__init__.py` to export pipeline:

```python
"""Core composition infrastructure."""

from .composer import LayeredComposer
from .discovery import LayerDiscovery, LayerSource
from .errors import CompositionValidationError, CompositionNotFoundError
from .modes import CompositionMode, ConcatenateComposer
from .paths import CompositionPathResolver, ResolvedPaths, get_resolved_paths
from .pipeline import CompositionPipeline
from .report import CompositionReport
from .schema import CompositionSchema
from .sections import SectionParser, SectionComposer, SectionRegistry, SectionMode
from .types import ComposeResult

__all__ = [
    # Composer
    "LayeredComposer",
    # Discovery
    "LayerDiscovery",
    "LayerSource",
    # Errors
    "CompositionValidationError",
    "CompositionNotFoundError",
    # Modes
    "CompositionMode",
    "ConcatenateComposer",
    # Paths
    "CompositionPathResolver",
    "ResolvedPaths",
    "get_resolved_paths",
    # Pipeline (NEW)
    "CompositionPipeline",
    "CompositionReport",
    # Schema
    "CompositionSchema",
    # Sections
    "SectionParser",
    "SectionComposer",
    "SectionRegistry",
    "SectionMode",
    # Types
    "ComposeResult",
]
```

Also update `src/edison/core/composition/__init__.py` to re-export:

```python
"""Edison composition system."""

# Re-export from core for convenience
from .core import (
    CompositionPipeline,
    CompositionReport,
    LayeredComposer,
    CompositionPathResolver,
    SectionParser,
)

__all__ = [
    "CompositionPipeline",
    "CompositionReport",
    "LayeredComposer",
    "CompositionPathResolver",
    "SectionParser",
]
```

### Step 10: Create Project Config for Wilson

Create `.edison/config/project.yml` in wilson-leadgen:

```yaml
# Wilson Lead Generation - Project Configuration
# Values accessible via {{config.path.to.value}} in templates

project:
  name: wilson-leadgen
  description: Lead generation dashboard
  packageManager: pnpm

  paths:
    root: .
    api: apps/api
    dashboard: apps/dashboard
    prisma: apps/dashboard/prisma

  database:
    tablePrefix: dashboard_
    timestampFields: true
    softDelete: true

  api:
    prefix: /api/v1/dashboard
    responseEnvelope: true

  auth:
    provider: better-auth
    roles:
      - ADMIN
      - OPERATOR
      - VIEWER

  models:
    primary:
      name: Lead
      pluralName: leads
    secondary:
      name: Source
      pluralName: sources

  imports:
    auth: "@/lib/auth"
    db: "@/lib/db"
    utils: "@/lib/utils"

context7:
  packages:
    prisma: /prisma/prisma
    nextjs: /vercel/next.js
    react: /facebook/react
    fastify: /fastify/fastify
    vitest: /vitest-dev/vitest
    tailwind: /tailwindlabs/tailwindcss
    betterAuth: /better-auth/better-auth
```

## Verification Checklist
- [ ] `CompositionPipeline` class created using existing infrastructure
- [ ] `CompositionReport` class created for unified reporting
- [ ] ALL 18 write points migrated to `pipeline.write()`
- [ ] Transformation order enforced (includes → sections → config → legacy)
- [ ] Config vars (`{{config.*}}`) substituted correctly
- [ ] Legacy vars (`{{source_layers}}`, etc.) substituted from context
- [ ] Section markers and Handlebars loops NOT touched
- [ ] Includes resolved recursively (max depth: 3)
- [ ] Missing variables tracked and reported
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Wilson project.yml created with all needed values
- [ ] `edison compose all` produces fully processed output
- [ ] Composition report shows no missing variables

## Testing Commands
```bash
cd /Users/leeroy/Documents/Development/edison

# Run unit tests
uv run pytest tests/unit/composition/test_pipeline.py -v

# Run all composition tests
uv run pytest tests/unit/composition/ -v

# Test in wilson-leadgen
cd /Users/leeroy/Documents/Development/wilson-leadgen

# Run composition
uv run --project ../edison edison compose all

# Check for unsubstituted variables
grep -r "{{config\." .edison/_generated/ | wc -l
# Should return 0

# Check composition report
uv run --project ../edison edison compose all --json | jq '.report'
```

## Success Criteria
1. Single `CompositionPipeline` class handles ALL template processing
2. ALL 18 write points use `pipeline.write()` or `pipeline.write_json()`
3. Transformation order is enforced consistently
4. Existing infrastructure is reused (ConfigManager, includes, sections, writes)
5. Unified report shows all activity across all files
6. Running `edison compose all` produces fully processed output with no missing variables

## Related Files
- WTPL-001 design specification (must complete first)
- `src/edison/core/config/manager.py` - ConfigManager (use, don't duplicate)
- `src/edison/core/composition/includes.py` - Include resolution
- `src/edison/core/composition/core/sections.py` - Section parsing
- `src/edison/core/utils/io/core.py` - write_text_locked
- `src/edison/core/utils/io/json.py` - write_json_atomic
- All 18 write point files listed above
