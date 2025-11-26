# AUDIT 5: Remediation Checklist

**Quick reference for executing the cleanup plan**

---

## 🔥 PHASE 1: CRITICAL DELETIONS

### Task 1.1: Remove Session Dual Layout System
**Effort:** 4-6 hours | **Priority:** 🔴 CRITICAL

#### Files to Modify:
- [ ] `src/edison/core/session/store.py`
- [ ] `src/edison/core/session/manager.py`
- [ ] `src/edison/core/session/discovery.py`

#### Steps:
```bash
# 1. Find affected tests
grep -rn "sessions/wip\|legacy_flat\|legacy.*json" tests/ --include="*.py"

# 2. Create migration script
# Script to convert flat layout to nested:
# .project/sessions/wip/session-123.json → .project/sessions/wip/session-123/session.json

# 3. Update store.py
# DELETE lines: 127, 164, 214-219, 283, 327-330, 351-382, 517-520
# REMOVE: All legacy flat file writes and lookups

# 4. Update manager.py
# DELETE lines: 99-102, 189-194, 217-219, 282

# 5. Update discovery.py
# DELETE lines: 95-102 (legacy wip path candidates)

# 6. Update tests to expect nested layout only

# 7. Run migration script on any existing flat files

# 8. Run full test suite
pytest tests/unit/session tests/integration/session -v
```

#### Success Criteria:
- [ ] No references to "legacy" in session store/manager
- [ ] Single file layout (nested only)
- [ ] All tests passing
- [ ] Migration script tested

---

### Task 1.2: Delete Compatibility Shim Modules
**Effort:** 2-3 hours | **Priority:** 🔴 CRITICAL

#### Files to Modify:
- [ ] `src/edison/core/__init__.py`
- [ ] `src/edison/core/utils/__init__.py`
- [ ] `src/edison/core/composition/__init__.py`

#### Steps:
```bash
# 1. Find cli_utils imports
grep -rn "from edison.core import cli_utils" . --include="*.py"
# Expected: tests/, maybe some scripts

# 2. Update imports
# OLD: from edison.core import cli_utils; cli_utils.run_command(...)
# NEW: from edison.core.utils.subprocess import run_command; run_command(...)

# 3. Find utils.cli imports
grep -rn "from edison.core.utils import cli" . --include="*.py"
# Update similarly

# 4. Find composition IDE imports
grep -rn "from edison.core.composition import.*Command\|from edison.core.composition import.*Hook" . --include="*.py"
# OLD: from edison.core.composition import CommandComposer
# NEW: from edison.core.ide.commands import CommandComposer

# 5. Delete shim code from __init__.py files
# core/__init__.py: DELETE lines 11-37, keep only exceptions export
# utils/__init__.py: DELETE lines 47-57
# composition/__init__.py: DELETE lines 17-28

# 6. Run tests
pytest -v
```

#### Success Criteria:
- [ ] Zero "compatibility shim" comments
- [ ] All imports updated
- [ ] All tests passing
- [ ] No runtime import errors

---

### Task 1.3: Remove SessionNamingStrategy Backward Compatibility
**Effort:** 1-2 hours | **Priority:** 🔴 CRITICAL

#### File to Modify:
- [ ] `src/edison/core/session/naming.py`

#### Steps:
```bash
# 1. Find SessionNamingStrategy usage
grep -rn "SessionNamingStrategy" . --include="*.py"

# 2. Analyze usage patterns
# Option A: Delete class entirely, use process inspector directly
# Option B: Keep class, remove deprecated parameters

# 3. If deleting class:
#    - Update callers to use process inspector
#    - Delete SessionNamingStrategy class
#    - Keep only helper functions

# 4. If keeping class:
#    - Remove config parameter from __init__
#    - Remove process, owner, existing_sessions, **kwargs from generate()
#    - Simplify to: def generate(self) -> str:
#    - Update docstrings

# 5. Run tests
pytest tests/unit/session/test_naming.py -v
```

#### Success Criteria:
- [ ] No "DEPRECATED" markers in naming.py
- [ ] No "backward compatibility" comments
- [ ] All tests passing
- [ ] Simpler API

---

## ⚡ PHASE 2: MODERATE CLEANUP

### Task 2.1: Delete Task Manager Facade
**Effort:** 1 hour | **Priority:** 🟡 MODERATE

```bash
# 1. Find TaskManager usage
grep -rn "from.*task.*import.*TaskManager\|TaskManager(" . --include="*.py"

# 2. Update tests
# OLD: mgr = TaskManager(); mgr.claim_task(task_id, session_id)
# NEW: import edison.core.task as task; task.claim_task(task_id, session_id)

# 3. Delete file
rm src/edison/core/task/manager.py

# 4. Remove from __init__.py if exported
# Check: grep "TaskManager" src/edison/core/task/__init__.py

# 5. Run tests
pytest tests/unit/task -v
```

---

### Task 2.2: Remove Task Metadata Compatibility Shim
**Effort:** 30 minutes | **Priority:** 🟡 MODERATE

```bash
# 1. Find imports
grep -rn "from.*task.metadata.*import.*find_record" . --include="*.py"

# 2. Update imports
# OLD: from edison.core.task.metadata import find_record
# NEW: from edison.core.task.finder import find_record

# 3. Delete shim (lines 315-319 in metadata.py)

# 4. Run tests
pytest tests/unit/task -v
```

---

### Task 2.3: Clean Up Task State Module
**Effort:** 30 minutes | **Priority:** 🟡 MODERATE

```bash
# 1. Check if task/state.py is still needed
grep -rn "from.*task.state.*import\|from.*task import.*state" . --include="*.py"

# 2. If unused or only in tests, delete
rm src/edison/core/task/state.py

# 3. If used, remove "legacy" comment from docstring

# 4. Run tests
pytest tests/unit/task -v
```

---

### Task 2.4: Remove project_TERMS Backward Compatibility
**Effort:** 30 minutes | **Priority:** 🟡 MODERATE

```bash
# 1. Find usage of global constant
grep -rn "project_TERMS" . --include="*.py" | grep -v "project_terms()"

# 2. Update to function call
# OLD: from edison.core.composition.audit import project_TERMS; if term in project_TERMS:
# NEW: from edison.core.composition.audit import project_terms; if term in project_terms():

# 3. Delete global from audit/__init__.py
# DELETE line: project_TERMS = project_terms()
# DELETE from __all__

# 4. Run tests
pytest tests/unit/composition/audit -v
```

---

## 📝 PHASE 3: COHERENCE IMPROVEMENTS

### Task 3.1: Rename discovery.py Files
**Effort:** 1 hour | **Priority:** 🟢 LOW

```bash
# Rename files
git mv src/edison/core/setup/discovery.py src/edison/core/setup/installer_discovery.py
git mv src/edison/core/composition/audit/discovery.py src/edison/core/composition/audit/guideline_discovery.py

# Update imports
grep -rn "from.*setup.discovery\|from.*audit.discovery" . --include="*.py"
# Update each import

# Run tests
pytest -v
```

---

### Task 3.2: Rename metadata.py Files
**Effort:** 1 hour | **Priority:** 🟢 LOW

```bash
# Rename file
git mv src/edison/core/composition/metadata.py src/edison/core/composition/guideline_metadata.py

# Update imports
grep -rn "from.*composition.metadata\|from.*composition import.*metadata" . --include="*.py"
# Update each import

# Run tests
pytest -v
```

---

### Task 3.3: Consider locking.py Consolidation
**Effort:** 1 hour | **Priority:** 🟢 LOW

```bash
# Option A: Rename task/locking.py
git mv src/edison/core/task/locking.py src/edison/core/task/task_locks.py
# Update imports

# Option B: Merge into task/io.py
# Move functions from task/locking.py to task/io.py
# Delete task/locking.py

# Evaluate which makes more sense based on function usage
grep -rn "from.*task.locking import" . --include="*.py"
```

---

## 📚 PHASE 4: DOCUMENTATION

### Task 4.1: Document Pack Trigger Format
**Effort:** 15 minutes | **Priority:** 🟢 LOW

```bash
# Edit composition/packs.py line 428
# Either:
# A) Remove Phase 2 legacy format support
# B) Document that both formats are intentionally supported

# Update docstrings and comments
```

---

### Task 4.2: Resolve Manager TODO
**Effort:** 15 minutes | **Priority:** 🟢 LOW

```bash
# Edit session/manager.py line 116
# TODO: Implement listing for other states in store

# Either:
# A) Implement the feature
# B) Remove TODO if not needed
# C) Create a proper issue and reference it
```

---

## ✅ VALIDATION CHECKLIST

After each phase, verify:

- [ ] All grep commands show zero results for legacy patterns
- [ ] Full test suite passes: `pytest -v`
- [ ] No import errors: `python -c "import edison.core"`
- [ ] No deprecation warnings in logs
- [ ] Documentation updated
- [ ] Git commits follow TDD (test update → implementation → refactor)

---

## 🔍 VERIFICATION COMMANDS

### After Phase 1:
```bash
# Should return ZERO results:
grep -rn "legacy.*flat.*file\|backward.*compat" src/edison/core/session --include="*.py"
grep -rn "from edison.core import cli_utils" . --include="*.py"
grep -rn "DEPRECATED" src/edison/core/session/naming.py

# Tests should pass:
pytest tests/unit/session tests/unit/task -v
```

### After Phase 2:
```bash
# Should return ZERO results:
grep -rn "TaskManager\|task.manager" src/edison --include="*.py" | grep -v test
grep -rn "for legacy tests" src/edison/core --include="*.py"
grep -rn "project_TERMS" src/edison/core --include="*.py" | grep -v "project_terms()"

# Tests should pass:
pytest -v
```

### After Phase 3:
```bash
# Should have consistent naming:
find src/edison/core -name "*discovery.py" -o -name "*metadata.py" -o -name "*locking.py"

# Tests should pass:
pytest -v
```

### Final Validation:
```bash
# Should return ZERO results:
grep -rn "legacy\|deprecated\|compat\|backward" src/edison/core --include="*.py" | grep -v "# " | grep -v legacy_guard.py

# Should return ZERO:
grep -rn "TODO\|FIXME\|HACK" src/edison/core --include="*.py" | wc -l

# All tests should pass:
pytest -v --cov=src/edison/core --cov-report=term-missing
```

---

## 📊 PROGRESS TRACKING

| Phase | Task | Status | Time | Notes |
|-------|------|--------|------|-------|
| 1 | Remove session dual layout | ⬜ | - | - |
| 1 | Delete compatibility shims | ⬜ | - | - |
| 1 | Clean SessionNamingStrategy | ⬜ | - | - |
| 2 | Delete TaskManager | ⬜ | - | - |
| 2 | Remove metadata shim | ⬜ | - | - |
| 2 | Clean task state | ⬜ | - | - |
| 2 | Remove project_TERMS | ⬜ | - | - |
| 3 | Rename discovery.py | ⬜ | - | - |
| 3 | Rename metadata.py | ⬜ | - | - |
| 3 | Consolidate locking.py | ⬜ | - | - |
| 4 | Document pack formats | ⬜ | - | - |
| 4 | Resolve TODO | ⬜ | - | - |

**Legend:** ⬜ Not Started | 🟦 In Progress | ✅ Complete | ❌ Blocked

---

## 🚨 TROUBLESHOOTING

### Issue: Tests failing after import changes
**Solution:**
```bash
# Find all imports of the old path
grep -rn "old.import.path" . --include="*.py"
# Update each one
```

### Issue: Session data not found after layout change
**Solution:**
```bash
# Run migration script
python scripts/migrate_session_layout.py --dry-run
python scripts/migrate_session_layout.py
```

### Issue: Import errors after shim deletion
**Solution:**
```bash
# Check if any imports were missed
python -c "import edison.core" 2>&1 | grep -i "cannot import"
# Update the imports shown in error
```

---

## 📋 DEFINITION OF DONE

All tasks complete when:

✅ All checklist items marked complete
✅ Zero legacy/backward/deprecated references in production code
✅ Zero failing tests
✅ Zero import errors
✅ Documentation updated
✅ Code review approved
✅ Changes merged to main branch

---

**REMEMBER:** Follow strict TDD for all changes:
1. Write/update failing test (RED)
2. Implement fix (GREEN)
3. Refactor (REFACTOR)
4. Commit
