---
name: validators-base
project: edison
overlay_type: extend
---

<!-- EXTEND: MandatoryReads -->

### Edison Project Critical Principles (MANDATORY)

**MANDATORY READ**: `guidelines/shared/PRINCIPLES_REFERENCE.md`

The 16 non-negotiable principles govern all Edison development. See PRINCIPLES_REFERENCE.md for the complete list and links to full documentation.

**Validator Focus:**
- **TDD**: Git history shows test-first pattern
- **NO MOCKS**: Reject any mock/patch usage
- **NO HARDCODING**: Config must be in YAML files
- **NO LEGACY**: Reject backward-compat code
- **ROOT CAUSE**: Reject workaround fixes
- **TOOLING**: mypy --strict, ruff, pytest must all pass

<!-- /EXTEND -->

<!-- NEW_SECTION: EdisonValidationChecklist -->

## Edison Project Validation Checklist

### BLOCKING Issues (Must Reject)

#### 1. Mock Usage Detection
```bash
# Search for forbidden patterns
grep -r "unittest.mock\|@patch\|Mock(\|MagicMock" src/ tests/
```
**If found: REJECT immediately**

#### 2. Hardcoded Values
```bash
# Check for magic numbers/strings in code (not config)
grep -rn "= [0-9]\+$\|https://\|http://" src/edison/
```
**If found in code (not YAML): REJECT**

#### 3. Type Check Failure
```bash
mypy --strict src/edison/
```
**If errors: REJECT**

#### 4. Test Failures
```bash
pytest tests/ -v
```
**If failures: REJECT**

#### 5. Lint Errors
```bash
ruff check src/edison/ tests/
```
**If errors: REJECT**

### WARNING Issues (Should Fix)

- Missing docstrings on public APIs
- Complex functions without comments
- Large modules that could be split

### Edison-Specific Patterns to Verify

1. **CLI Commands**
   - Has `register_args()` and `main()` functions
   - Returns proper exit codes
   - No hardcoded values

2. **Configuration**
   - Uses ConfigManager or domain accessors
   - No magic numbers
   - Config in YAML files

3. **Entities**
   - Inherit from BaseEntity
   - Have `to_dict()` and `from_dict()`
   - Use state machines

4. **Composition**
   - Proper section markers
   - Overlays extend correctly
   - Pack structure valid

<!-- /NEW_SECTION -->
