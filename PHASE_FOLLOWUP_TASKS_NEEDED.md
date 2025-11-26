1. Wrap all scripts with cli_utils.run_cli() (5 hours)
- 15 scripts still use direct if __name__ == "__main__": main()
- Benefit: Consistent error handling and JSON mode
2. Add tests for 5 utility scripts (4 hours)
- tasks/split, tasks/link, tasks/mark-delegated
- Coverage would increase to 90%+
3. Create shared argparse parent parsers (3 hours)
- Reduce duplication of --session, --json, --dry-run args
1. Add help text (4-6 hours)
- To 5-10 high-use scripts
- Currently only 1.6% have it
2. Fix executable bits (10 minutes)
- 15 scripts not executable
- Mostly migration/utility scripts
3. Add shebangs (5 minutes)
- 4 utility scripts missing
- All migration scripts
4. Add db/ tests (4-6 hours)
- Regression protection
- For shell=True fixes
5. Archive migrations (1 hour)
- Move to tools/migrations/
- Clean up directories

Task/Session Cross-Dependencies (3 cycles) - NOT FIXED
The remaining 3 circular dependencies require protocol/interface extraction:
1. task.api → session.config → ...
2. session.store → task → task.api
3. session.recovery → task → task.api
4. session.graph → task → task.api
Recommended Fix (from audit):
Create protocol files defining interfaces:
- protocols/task_protocol.py with TaskStoreProtocol
- protocols/session_protocol.py with SessionStoreProtocol
Estimated Effort: 5-8 hours
This is a more complex refactor that requires:
- Defining clear interface contracts
- Updating both task and session modules to use protocols
- Ensuring backwards compatibility
- Comprehensive testing

1. Remove Dead Code 🗑️ EASY WIN
- Impact: -1,200 lines (7% of codebase)
- Effort: 1 week
- Risk: LOW

### 1. DRY VIOLATIONS - 1,315 Lines of Duplication
#### **CRITICAL Duplications (High Impact)**
**#1: Triple Implementation of Atomic Write**
- **Locations:** `io_utils.py`, `utils/json_io.py`, `task/api.py`
- **Lines Duplicated:** 95 lines
- **Impact:** Reliability bugs, maintenance burden
- **Recommendation:** Consolidate into single `io_utils._atomic_write()`
**#2: Duplicate Lock Management**
- **Locations:** `locklib.py`, `utils/json_io.py`
- **Lines Duplicated:** 50 lines
- **Impact:** Inconsistent locking behavior
- **Recommendation:** Remove `json_io._exclusive_lock`, use `locklib` everywhere
**#3: Registry Pattern Triplication**
- **Locations:** `state/guards.py`, `state/conditions.py`, `state/actions.py`
- **Lines Duplicated:** 90 lines
- **Impact:** Obscures validation logic
- **Recommendation:** Create generic `CallableRegistry<T>` base class
**#4: Render Method Duplication**
- **Locations:** All 4 adapters (claude, codex, cursor, zen)
- **Lines Duplicated:** 164 lines
- **Impact:** API bloat, inconsistency
- **Recommendation:** Extract to base class template methods
**#5: Git Root Detection**
- **Locations:** `paths/resolver.py`, `utils/git.py`
- **Lines Duplicated:** 54 lines
- **Impact:** Inconsistent path resolution
- **Recommendation:** Single implementation in `utils/git.py`
**Total Critical DRY Violations:** ~450 lines
#### **MAJOR Duplications** (45 items)
- Directory creation pattern: 71 occurrences across 27 files
- JSON read patterns: 40 lines across 4 files
- Validation logic: 380 lines across 5 files
- Session path resolution: 40 lines duplicated
- File move operations: 60 lines duplicated
**DRY Violation Summary:**
- **Critical (>20 lines):** 5 violations, ~450 lines
- **Major (10-20 lines):** 18 violations, ~500 lines
- **Minor (3-10 lines):** 22 violations, ~365 lines
- **TOTAL:** 45 violations, **~1,315 lines of duplicated code**
---
### 2. KISS VIOLATIONS - 26 Over-Engineering Issues
#### **CRITICAL Over-Engineering**
**#1: Three-Layer Registry with Single Implementation**
- **Location:** `state/guards.py`, `state/conditions.py`, `state/actions.py`
- **Issue:** Complex registration API for 6 static guards
- **Savings:** 250 lines → 30 lines
- **Recommendation:** Direct function lookup dict

**#3: CompositionEngine Monolith**
- **Location:** `composition.py` (1,450 lines)
- **Issue:** 11 different responsibilities in one file
- **Recommendation:** Split into 5 focused modules (~200 lines each)

### 3. YAGNI VIOLATIONS - 1,200 Lines of Dead Code
#### **HIGH PRIORITY Removals**
**Dead Classes:**
1. `CircuitBreaker` (resilience.py) - 80 lines, 0 instantiations
2. `WorktreeManager` (worktreelib.py) - 120 lines, 0 instantiations
3. `GitOperations` (git/operations.py) - Unknown lines, 0 instantiations
4. `PromptAdapter` base (adapters/base.py) - 200 lines, 0 uses
5. `SessionContext` - 0 instantiations
**Dead Functions (Sample):**
- `archive_worktree()` - 0 calls
- `atomic_write_json()` - 0 calls (task/api.py)
- `auto_session_for_owner()` - 0 calls
- `build_validation_bundle()` - 0 calls
- `claim_task_with_lock()` - 0 calls
- `cleanup_expired_sessions()` - 0 calls
- 30+ more unused functions identified

1. Split `task/api.py` (966 lines - still too large)
- Target: 5-6 focused modules
- Effort: 1 week
2. Deprecations
- Old module names still present -> remove/refactor

1. Complete Domain Model Coverage
- Expand beyond 5 dataclasses
- Add: Session, Task, ValidationBundle, ValidatorRoster
- Effort: 2 weeks

3. Add Protocol Interfaces
- SessionStore, TaskStore, QAStore protocols
- Effort: 1 week



