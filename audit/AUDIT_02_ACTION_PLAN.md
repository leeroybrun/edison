# AUDIT 02: Action Plan - Hardcoded Values Remediation

**Created:** 2025-11-26
**Priority:** CRITICAL
**Estimated Total Effort:** 36 hours (~4.5 days)

---

## QUICK START CHECKLIST

### Phase 1: Add Missing Config (Day 1 - 6 hours)
- [ ] Add `file_io.*` section to defaults.yaml
- [ ] Add `composition.dry.*` section to defaults.yaml
- [ ] Add `filenames.*` section to defaults.yaml
- [ ] Add `patterns.*` section to defaults.yaml
- [ ] Add `extensions.*` section to defaults.yaml
- [ ] Add `commands.*` section to defaults.yaml
- [ ] Add `qa.scoring.*` section to defaults.yaml
- [ ] Add `debug.*` section to defaults.yaml
- [ ] Add `subprocess.cache_size` to defaults.yaml
- [ ] Validate YAML syntax

### Phase 2: Update Core Utilities (Day 2 - 8 hours)
- [ ] Fix `utils/resilience.py` - use config for retry params
- [ ] Fix `utils/subprocess.py` - remove env vars, use config
- [ ] Fix `utils/text.py` - use config for DRY detection
- [ ] Fix `utils/json_io.py` - use config for lock timeout
- [ ] Fix `file_io/locking.py` - use config for lock params
- [ ] Add tests for each config integration

### Phase 3: Update Path & IDE Modules (Day 3 - 8 hours)
- [ ] Create `PathConfig` class for centralized path access
- [ ] Update `ide/hooks.py` - use PathConfig
- [ ] Update `ide/settings.py` - use PathConfig
- [ ] Update `ide/commands.py` - use PathConfig + config limits
- [ ] Update `paths/resolver.py` - use config for limits
- [ ] Update `paths/project.py` - use config
- [ ] Add tests for path resolution

### Phase 4: Update Composition & QA (Day 4 - 8 hours)
- [ ] Update `composition/includes.py` - use config for MAX_DEPTH
- [ ] Update `composition/agents.py` - remove EDISON_DRY_MIN_SHINGLES
- [ ] Update `composition/composers.py` - remove EDISON_DRY_MIN_SHINGLES
- [ ] Update `composition/guidelines.py` - remove EDISON_DRY_MIN_SHINGLES
- [ ] Update `qa/scoring.py` - use config for thresholds
- [ ] Update `qa/bundler.py` - use config for patterns
- [ ] Update `qa/transaction.py` - use config for patterns
- [ ] Add tests for composition and QA

### Phase 5: Cleanup & Documentation (Day 5 - 6 hours)
- [ ] Remove all environment variable fallbacks (except AGENTS_PROJECT_ROOT)
- [ ] Update documentation for config override pattern
- [ ] Add config validation schema
- [ ] Run full test suite
- [ ] Create migration guide
- [ ] Update CLAUDE.md with config-first enforcement

---

## DETAILED TASK BREAKDOWN

## TASK 1: Add File I/O Configuration to defaults.yaml

**File:** `src/edison/data/config/defaults.yaml`
**Location:** After line 577 (after `time:` section)
**Estimated Time:** 30 minutes

```yaml
# File I/O and locking configuration
file_io:
  locking:
    timeout_seconds: 10.0
    poll_interval: 0.1
    nfs_safe: true
    fail_open: false
  json:
    lock_timeout_seconds: 5.0
```

**Validation:**
```bash
python -c "import yaml; yaml.safe_load(open('src/edison/data/config/defaults.yaml'))"
```

---

## TASK 2: Add Composition Configuration to defaults.yaml

**File:** `src/edison/data/config/defaults.yaml`
**Estimated Time:** 30 minutes

```yaml
# Composition system configuration
composition:
  dry:
    shingle_size: 12
    min_shingles: 2
    strip_headings: true
    strip_code_blocks: true
  max_include_depth: 3
  cache:
    enabled: true
    ttl_seconds: 3600
```

---

## TASK 3: Add Filenames & Patterns Configuration

**File:** `src/edison/data/config/defaults.yaml`
**Estimated Time:** 30 minutes

```yaml
# Standard filenames used throughout the system
filenames:
  session: "session.json"
  task: "task.json"
  orchestrator_manifest: "orchestrator-manifest.json"
  settings: "settings.json"
  hooks: "hooks.yaml"
  commands: "commands.yml"
  pack: "pack.yml"

# File patterns and templates
patterns:
  round_directory: "round-{round}"
  validator_report: "validator-{name}-report.json"
  evidence_glob: "round-*"
  session_prefix: "session-"
  task_prefix: "task-"

# File extensions
extensions:
  config_primary: ".yaml"
  config_secondary: ".yml"
  data: ".json"
  documentation: ".md"
  template_suffix: ".template"
  lock_suffix: ".lock"
```

---

## TASK 4: Fix Resilience Retry Logic

**File:** `src/edison/core/utils/resilience.py`
**Estimated Time:** 2 hours
**Priority:** P1 CRITICAL

### Current Code (Lines 19-24):
```python
def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
```

### Updated Code:
```python
def retry_with_backoff(
    max_attempts: Optional[int] = None,
    initial_delay: Optional[float] = None,
    backoff_factor: Optional[float] = None,
    max_delay: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    config: Optional[Dict[str, Any]] = None,
):
    """Decorator that retries a function with exponential backoff.

    All parameters are configurable via defaults.yaml:resilience.retry.*
    Function arguments override config values.
    """
    if config is None:
        from ..config import ConfigManager
        cfg = ConfigManager().load_config(validate=False)
        retry_cfg = cfg.get("resilience", {}).get("retry", {})
    else:
        retry_cfg = config.get("resilience", {}).get("retry", {})

    max_attempts = max_attempts or retry_cfg.get("max_attempts", 3)
    initial_delay = initial_delay or retry_cfg.get("initial_delay_seconds", 1.0)
    backoff_factor = backoff_factor or retry_cfg.get("backoff_factor", 2.0)
    max_delay = max_delay or retry_cfg.get("max_delay_seconds", 60.0)
```

### Test:
```python
# Test that config is used
def test_retry_uses_config(tmp_path):
    config = {
        "resilience": {
            "retry": {
                "max_attempts": 5,
                "initial_delay_seconds": 2.0,
            }
        }
    }
    # Verify decorator uses config values
```

---

## TASK 5: Fix File Locking Parameters

**File:** `src/edison/core/file_io/locking.py`
**Estimated Time:** 2 hours
**Priority:** P1 CRITICAL

### Current Code (Lines 27-34):
```python
@contextmanager
def acquire_file_lock(
    file_path: Path | str,
    timeout: float = 10.0,
    nfs_safe: bool = True,
    *,
    fail_open: bool = False,
    poll_interval: float = 0.1,
) -> Iterator[Optional[object]]:
```

### Updated Code:
```python
@contextmanager
def acquire_file_lock(
    file_path: Path | str,
    timeout: Optional[float] = None,
    nfs_safe: Optional[bool] = None,
    *,
    fail_open: Optional[bool] = None,
    poll_interval: Optional[float] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Iterator[Optional[object]]:
    """Acquire an exclusive lock on ``file_path`` with a timeout.

    All parameters are configurable via defaults.yaml:file_io.locking.*
    """
    if config is None:
        from ..config import ConfigManager
        cfg = ConfigManager().load_config(validate=False)
        lock_cfg = cfg.get("file_io", {}).get("locking", {})
    else:
        lock_cfg = config.get("file_io", {}).get("locking", {})

    timeout = timeout if timeout is not None else lock_cfg.get("timeout_seconds", 10.0)
    nfs_safe = nfs_safe if nfs_safe is not None else lock_cfg.get("nfs_safe", True)
    fail_open = fail_open if fail_open is not None else lock_cfg.get("fail_open", False)
    poll_interval = poll_interval if poll_interval is not None else lock_cfg.get("poll_interval", 0.1)
```

---

## TASK 6: Remove Environment Variable Duplication in subprocess.py

**File:** `src/edison/core/utils/subprocess.py`
**Estimated Time:** 2 hours
**Priority:** P1 CRITICAL

### Remove Lines 29-30:
```python
# DELETE THESE:
DEFAULT_GIT_TIMEOUT = float(os.environ.get("EDISON_GIT_TIMEOUT_SECONDS", "60"))
DEFAULT_DB_TIMEOUT = float(os.environ.get("EDISON_DB_TIMEOUT_SECONDS", "30"))
```

### Update `_load_timeouts()` function (keep as-is, it already uses config)

### Update `configured_timeout()` to NOT check env vars

**Note:** The config system already supports `EDISON_*` overrides via ConfigManager._build_env_overrides(), so environment variables still work but go through the proper config layer.

---

## TASK 7: Fix JSON I/O Lock Timeout

**File:** `src/edison/core/utils/json_io.py`
**Estimated Time:** 1 hour
**Priority:** P1 CRITICAL

### Replace Line 33:
```python
# DELETE:
_LOCK_TIMEOUT_SECONDS = float(os.environ.get("EDISON_JSON_IO_LOCK_TIMEOUT", 5.0))

# REPLACE WITH:
def _get_lock_timeout(config: Optional[Dict[str, Any]] = None) -> float:
    if config is None:
        from edison.core.config import ConfigManager
        config = ConfigManager().load_config(validate=False)
    return float(config.get("file_io", {}).get("json", {}).get("lock_timeout_seconds", 5.0))
```

### Update all usages of `_LOCK_TIMEOUT_SECONDS`:
```python
# In _lock_context function (line 39):
return locklib.acquire_file_lock(
    path, timeout=_get_lock_timeout(), fail_open=True
)
```

---

## TASK 8: Fix Text Processing DRY Detection

**File:** `src/edison/core/utils/text.py`
**Estimated Time:** 2 hours
**Priority:** P2 HIGH

### Update `_shingles()` function (line 39):
```python
def _shingles(words: List[str], k: Optional[int] = None, config: Optional[Dict[str, Any]] = None) -> Set[Tuple[str, ...]]:
    """Generate k-word shingles from a list of words.

    Args:
        k: Shingle size. If None, uses config value (default: 12)
    """
    if k is None:
        if config is None:
            from ..config import ConfigManager
            config = ConfigManager().load_config(validate=False)
        k = int(config.get("composition", {}).get("dry", {}).get("shingle_size", 12))

    if k <= 0 or len(words) < k:
        return set()
    return {tuple(words[i : i + k]) for i in range(0, len(words) - k + 1)}
```

### Update `dry_duplicate_report()` function (line 46):
```python
def dry_duplicate_report(
    sections: Dict[str, str],
    *,
    min_shingles: Optional[int] = None,
    k: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict:
    """Return duplication report between sections using shingled hashes.

    All parameters configurable via defaults.yaml:composition.dry.*
    """
    if config is None:
        from ..config import ConfigManager
        config = ConfigManager().load_config(validate=False)

    dry_cfg = config.get("composition", {}).get("dry", {})
    min_shingles = min_shingles or int(dry_cfg.get("min_shingles", 2))
    k = k or int(dry_cfg.get("shingle_size", 12))
```

---

## TASK 9: Remove EDISON_DRY_MIN_SHINGLES from Multiple Files

**Files:**
- `src/edison/core/composition/agents.py:278`
- `src/edison/core/composition/composers.py:149`
- `src/edison/core/composition/guidelines.py:358`

**Estimated Time:** 2 hours
**Priority:** P1 CRITICAL

### In each file, replace:
```python
# DELETE:
int(os.environ.get("EDISON_DRY_MIN_SHINGLES", "2"))

# REPLACE WITH:
# Import at top of file:
from ..utils.text import dry_duplicate_report

# Then use the function which now reads from config:
dry_duplicate_report(sections, config=config)
# OR if you need just the value:
config.get("composition", {}).get("dry", {}).get("min_shingles", 2)
```

---

## TASK 10: Fix MAX_DEPTH in includes.py

**File:** `src/edison/core/composition/includes.py`
**Estimated Time:** 1 hour
**Priority:** P2 HIGH

### Replace Line 18:
```python
# DELETE:
MAX_DEPTH = 3

# REPLACE WITH function that reads config:
def _get_max_depth(config: Optional[Dict[str, Any]] = None) -> int:
    if config is None:
        from ..config import ConfigManager
        config = ConfigManager().load_config(validate=False)
    return int(config.get("composition", {}).get("max_include_depth", 3))
```

### Update all usages of `MAX_DEPTH` to call `_get_max_depth()`

---

## TASK 11: Create PathConfig Utility Class

**New File:** `src/edison/core/paths/config.py`
**Estimated Time:** 3 hours
**Priority:** P1 CRITICAL

```python
"""Centralized path configuration access."""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache


class PathConfig:
    """Centralized access to all path-related configuration.

    This class ensures all directory names, filenames, and patterns
    come from configuration rather than hardcoded values.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            from ..config import ConfigManager
            config = ConfigManager().load_config(validate=False)
        self._config = config

    # Directory names
    @property
    def edison_dir(self) -> str:
        return str(self._config.get("paths", {}).get("project_config_dir", ".edison"))

    @property
    def claude_output_dir(self) -> str:
        return str(self._config.get("adapters", {}).get("claude", {}).get("output_dir", ".claude"))

    @property
    def cursor_output_dir(self) -> str:
        return str(self._config.get("adapters", {}).get("cursor", {}).get("output_dir", ".cursor/prompts"))

    @property
    def codex_output_dir(self) -> str:
        return str(self._config.get("adapters", {}).get("codex", {}).get("output_dir", ".codex"))

    @property
    def zen_output_dir(self) -> str:
        return str(self._config.get("adapters", {}).get("zen", {}).get("output_dir", ".zen/conf/systemprompts/clink/project"))

    # Filenames
    @property
    def session_filename(self) -> str:
        return str(self._config.get("filenames", {}).get("session", "session.json"))

    @property
    def task_filename(self) -> str:
        return str(self._config.get("filenames", {}).get("task", "task.json"))

    @property
    def orchestrator_manifest_filename(self) -> str:
        return str(self._config.get("filenames", {}).get("orchestrator_manifest", "orchestrator-manifest.json"))

    # Patterns
    def round_directory(self, round_num: int) -> str:
        pattern = self._config.get("patterns", {}).get("round_directory", "round-{round}")
        return pattern.format(round=round_num)

    def validator_report(self, validator_name: str) -> str:
        pattern = self._config.get("patterns", {}).get("validator_report", "validator-{name}-report.json")
        return pattern.format(name=validator_name)

    @property
    def evidence_glob_pattern(self) -> str:
        return str(self._config.get("patterns", {}).get("evidence_glob", "round-*"))


# Global instance (lazy-loaded)
_PATH_CONFIG: Optional[PathConfig] = None

def get_path_config(config: Optional[Dict[str, Any]] = None) -> PathConfig:
    """Get global PathConfig instance."""
    global _PATH_CONFIG
    if _PATH_CONFIG is None or config is not None:
        _PATH_CONFIG = PathConfig(config)
    return _PATH_CONFIG
```

---

## TASK 12: Update All Files to Use PathConfig

**Estimated Time:** 6 hours
**Priority:** P1 CRITICAL

### Files to Update:
1. `src/edison/core/ide/hooks.py`
2. `src/edison/core/ide/settings.py`
3. `src/edison/core/ide/commands.py`
4. `src/edison/core/paths/resolver.py`
5. `src/edison/core/paths/project.py`
6. `src/edison/core/qa/bundler.py`
7. `src/edison/core/qa/transaction.py`
8. All adapter files

### Example Update (hooks.py):
```python
# Add import at top:
from ..paths.config import get_path_config

# In __init__:
def __init__(self, repo_root: Optional[Path] = None):
    self.repo_root = repo_root or _repo_root()
    path_cfg = get_path_config()

    # BEFORE:
    # self.core_dir = self.repo_root / ".edison" / "core"

    # AFTER:
    self.core_dir = self.repo_root / path_cfg.edison_dir / "core"
    self.packs_dir = self.repo_root / path_cfg.edison_dir / "packs"
```

---

## TASK 13: Add Configuration Validation

**New File:** `src/edison/core/config_validator.py`
**Estimated Time:** 3 hours
**Priority:** P3 MEDIUM

```python
"""Configuration validation and schema enforcement."""
from pathlib import Path
from typing import Dict, Any, List
import yaml


REQUIRED_CONFIG_KEYS = [
    "edison.version",
    "paths.project_config_dir",
    "resilience.retry.max_attempts",
    "subprocess_timeouts.default",
    "file_io.locking.timeout_seconds",
]

NUMERIC_CONSTRAINTS = {
    "resilience.retry.max_attempts": (1, 10),
    "file_io.locking.timeout_seconds": (0.1, 300),
    "composition.dry.shingle_size": (1, 100),
}


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate configuration and return list of errors."""
    errors = []

    # Check required keys
    for key in REQUIRED_CONFIG_KEYS:
        if not _has_nested_key(config, key):
            errors.append(f"Missing required config key: {key}")

    # Check numeric constraints
    for key, (min_val, max_val) in NUMERIC_CONSTRAINTS.items():
        value = _get_nested_key(config, key)
        if value is not None:
            try:
                num = float(value)
                if not (min_val <= num <= max_val):
                    errors.append(
                        f"Config key {key}={num} out of range [{min_val}, {max_val}]"
                    )
            except (ValueError, TypeError):
                errors.append(f"Config key {key} must be numeric, got: {type(value)}")

    return errors


def _has_nested_key(d: Dict, key: str) -> bool:
    """Check if nested key exists (e.g., 'a.b.c')."""
    parts = key.split(".")
    curr = d
    for part in parts:
        if not isinstance(curr, dict) or part not in curr:
            return False
        curr = curr[part]
    return True


def _get_nested_key(d: Dict, key: str) -> Any:
    """Get nested key value."""
    parts = key.split(".")
    curr = d
    for part in parts:
        if not isinstance(curr, dict):
            return None
        curr = curr.get(part)
        if curr is None:
            return None
    return curr
```

---

## TASK 14: Update Tests

**Estimated Time:** 4 hours
**Priority:** P2 HIGH

### Create Test File: `tests/unit/config/test_hardcoded_compliance.py`

```python
"""Tests to ensure no hardcoded values exist."""
import pytest
from edison.core.config import ConfigManager
from edison.core.utils.resilience import retry_with_backoff
from edison.core.file_io.locking import acquire_file_lock
from edison.core.utils.text import dry_duplicate_report


def test_resilience_uses_config():
    """Verify retry logic uses config values."""
    config = {
        "resilience": {
            "retry": {
                "max_attempts": 7,
                "initial_delay_seconds": 3.0,
            }
        }
    }

    # Create decorator with config
    @retry_with_backoff(config=config)
    def test_func():
        raise ValueError("test")

    # Verify it uses config values (this will fail after 7 attempts, not 3)
    # Test implementation needed


def test_file_locking_uses_config():
    """Verify file locking uses config values."""
    config = {
        "file_io": {
            "locking": {
                "timeout_seconds": 20.0,
                "poll_interval": 0.5,
            }
        }
    }
    # Test implementation needed


def test_dry_detection_uses_config():
    """Verify DRY detection uses config values."""
    config = {
        "composition": {
            "dry": {
                "shingle_size": 15,
                "min_shingles": 5,
            }
        }
    }

    result = dry_duplicate_report(
        {"core": "test content", "packs": "test content"},
        config=config
    )
    assert result["k"] == 15
    assert result["minShingles"] == 5
```

---

## TASK 15: Documentation Updates

**File:** `docs/CONFIGURATION.md` (create if not exists)
**Estimated Time:** 3 hours
**Priority:** P3 MEDIUM

### Content:
```markdown
# Edison Configuration Guide

## Overview
All Edison behavior is configurable via YAML files. NO hardcoded values are allowed.

## Configuration Priority
1. Environment variables: `EDISON_<path>__<to>__<key>`
2. Project overrides: `<project>/.edison/config/*.yml`
3. Core defaults: `src/edison/data/config/defaults.yaml`

## Environment Variable Override Pattern
```bash
# Override any config key using EDISON_ prefix with __ as separator
EDISON_resilience__retry__max_attempts=5
EDISON_file_io__locking__timeout_seconds=20.0
```

## Adding New Configuration
1. Add to `defaults.yaml` with sensible default
2. Update code to use `ConfigManager().load_config()`
3. Add validation in `config_validator.py`
4. Add tests in `tests/unit/config/`
5. NEVER use hardcoded fallback values

## Common Patterns
[... detailed examples ...]
```

---

## TASK 16: Update CLAUDE.md

**File:** `CLAUDE.md`
**Estimated Time:** 30 minutes
**Priority:** P2 HIGH

### Add to "CRITICAL PRINCIPLES":
```markdown
13. ✅ **CONFIG-FIRST**: ALL values from YAML - ZERO tolerance for hardcoded magic numbers/strings
    - Before adding any numeric literal, check if it should be in defaults.yaml
    - Use ConfigManager for ALL runtime configuration
    - Environment variables ONLY for overrides via EDISON_* pattern
    - NO inline defaults except 0, 1, -1, True, False, None
```

---

## VERIFICATION CHECKLIST

After completing all tasks, verify:

- [ ] Run full test suite: `pytest tests/`
- [ ] Validate defaults.yaml: `python -c "import yaml; yaml.safe_load(open('src/edison/data/config/defaults.yaml'))"`
- [ ] Search for hardcoded timeouts: `grep -r "timeout.*[0-9]" src/edison/core --include="*.py" | wc -l` (should be minimal)
- [ ] Search for environment variables: `grep -r "os.environ.get" src/edison/core --include="*.py" | grep -v AGENTS_PROJECT_ROOT | wc -l` (should be 0)
- [ ] Search for magic numbers: `grep -rn "= [0-9]\+\." src/edison/core --include="*.py" | grep -v "0.0\|1.0" | wc -l` (should be minimal)
- [ ] Run configuration validator: `python -m edison.core.config_validator`
- [ ] Code review all changes

---

## ROLLBACK PLAN

If issues occur:

1. **Immediate Rollback:**
   ```bash
   git revert <commit-hash>
   ```

2. **Partial Rollback:**
   - Revert specific file changes
   - Keep config additions in defaults.yaml
   - Restore environment variable fallbacks temporarily

3. **Migration Path:**
   - Phase 1: Add config (safe, non-breaking)
   - Phase 2: Update code to use config (test each module)
   - Phase 3: Remove hardcoded fallbacks (after verification)

---

## SUCCESS METRICS

### Before (Current State)
- Hardcoded values: 83
- Config compliance: 48.2%
- Environment vars as primary config: 30+
- Files using hardcoded paths: 50+

### After (Target State)
- Hardcoded values: <5 (only true constants)
- Config compliance: 98%
- Environment vars as primary config: 1 (AGENTS_PROJECT_ROOT)
- Files using hardcoded paths: 0

### Measurement
```bash
# Run audit script to measure compliance
python scripts/audit_hardcoded_values.py
```

---

**End of Action Plan**
