TASK: Fix CRITICAL hardcoded `.agents` bypass #3 - cli/compose/all.py

Using STRICT TDD (RED → GREEN → REFACTOR):

## Target: `src/edison/cli/compose/all.py`
This file hardcodes generation output to `.agents/_generated`.

### RED PHASE:
1. Write failing test(s) that verify:
   - Generated files go to `{resolved_config_dir}/_generated`
   - NOT hardcoded to `.agents/_generated`

2. Run tests to confirm FAILURE (RED)

### GREEN PHASE:
3. Refactor `src/edison/cli/compose/all.py`:
   - Use `get_project_config_dir`
   - Replace hardcoded output path

4. Run tests to confirm PASSING (GREEN)

### Report:
- Test file path and test code
- Implementation changes (code diffs)
- Test results showing RED → GREEN
- Regression test results
- Any issues encountered

NO backward compatibility. NO fallbacks. Clean removal of hardcoded `.agents`.