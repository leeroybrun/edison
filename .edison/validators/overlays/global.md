---
name: global
project: edison
overlay_type: extend
---

<!-- EXTEND: TechStack -->

## Edison Framework Architecture

### CLI Commands
- Commands auto-discovered from `src/edison/cli/`
- Each command has `register_args()` and `main()`
- Commands follow existing patterns in the codebase

### Configuration System
- All config in YAML files (`.edison/config/`)
- Domain accessors for typed access
- No hardcoded values in code

### Entity System
- Inherit from BaseEntity
- State machine transitions
- JSON persistence with state history

### Composition System
- Section markers: `{{SECTION:Name}}`
- Overlays extend base documents
- Layered composition (core → pack → project)

<!-- /EXTEND -->

<!-- NEW_SECTION: EdisonChecks -->

## Edison Architecture Validation

### 1. CLI Command Structure

**Check:**
- Commands in `src/edison/cli/{domain}/{command}.py`
- Has `register_args(parser)` function
- Has `main(args) -> int` function
- Returns proper exit codes

**Fail if:**
- Missing required functions
- Incorrect function signatures
- Hardcoded values in commands

### 2. Configuration System

**Check:**
- Config loaded from YAML
- Domain accessors used
- No hardcoded URLs, paths, credentials
- JSON schema validation where applicable

**Fail if:**
- Hardcoded configuration values
- Magic numbers without constants
- Missing config accessor

### 3. Entity Pattern

**Check:**
- Entities inherit BaseEntity
- State machines used for lifecycle
- State history recorded
- JSON serialization correct

**Fail if:**
- Entity doesn't inherit BaseEntity
- State transitions bypassed
- Missing to_dict/from_dict

### 4. Composition System

**Check:**
- Section markers: `{{SECTION:Name}}`
- Overlay files follow conventions
- HTML comments for EXTEND/NEW_SECTION
- Pack structure correct

**Fail if:**
- Invalid section marker syntax
- Overlay doesn't match base
- Pack missing required files

### 5. CLAUDE.md Compliance

**CRITICAL - Must verify:**
- [ ] STRICT TDD: Tests written before implementation
- [ ] NO MOCKS: Real behavior tested
- [ ] NO HARDCODING: Config from YAML
- [ ] NO LEGACY: Old code deleted
- [ ] DRY: No code duplication
- [ ] ROOT CAUSE: Issues fixed at source

**Fail if:**
- Mock usage detected (unittest.mock, @patch)
- Hardcoded values found
- Legacy/backward-compat code
- Code duplication

<!-- /NEW_SECTION -->
