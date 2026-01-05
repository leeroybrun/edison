---
name: global
pack: python
overlay_type: extend
---

<!-- extend: tech-stack -->

## Python Technology Stack

### Evidence First (Do Not Overwrite)

Automation evidence is captured by the orchestrator via `edison evidence capture` into the current evidence round.
As a validator:
- **Do not re-run CI commands to generate `command-*.txt` files**
- **Do not overwrite evidence files**
- **Review the existing evidence artifacts in this evidence round directory**

If required evidence files are missing, reject and instruct the orchestrator to run `edison evidence capture <task>` (or re-run the validation round).

### Type Checking

```bash
sed -n '1,160p' {{fn:evidence_file("type-check")}}
```

**Validation Points:**
- All functions have type annotations
- Return types specified
- No `Any` without justification
- No `# type: ignore` without comment
- Generics used correctly

### Linting

```bash
sed -n '1,200p' {{fn:evidence_file("lint")}}
```

**Validation Points:**
- Evidence exists and is parseable (frontmatter includes `exitCode`)
- If lint is configured as non-blocking evidence (e.g. exit-zero), treat findings as **warnings** unless they indicate real defects

### Testing

```bash
tail -200 {{fn:evidence_file("test")}}
```

**Validation Points:**
- All tests passing
- Follow the core NO MOCKS policy (mock only system boundaries)
- Real files/databases used
- Edge cases covered

### Build

```bash
tail -200 {{fn:evidence_file("build")}}
```

<!-- /extend -->

<!-- section: PythonChecks -->

## Python-Specific Validation

### 1. Type Safety (BLOCKING)

**Evidence:** `{{fn:evidence_file("type-check")}}`

**Must Pass:**
- All function parameters have types
- All return types specified
- No `Any` without `# Reason: ...` comment
- No `# type: ignore` without explanation
- Modern syntax: `list[T]` not `List[T]`
- Modern syntax: `T | None` not `Optional[T]`

**Fail Conditions:**
- Any mypy error
- Unjustified `Any` usage
- Unjustified `# type: ignore`

### 2. Testing (BLOCKING)

**Evidence:** `{{fn:evidence_file("test")}}`

**Must Pass:**
- 100% test pass rate
- No skipped tests without reason
- Follow the core NO MOCKS policy (mock only system boundaries)
- Fixtures use real resources (tmp_path, real DBs)

**Fail Conditions:**
- Any failing test
- Mock usage detected (`unittest.mock`, `@patch`)
- Skipped tests without `@pytest.mark.skip(reason="...")`

### 3. Code Quality (BLOCKING)

**Evidence:** `{{fn:evidence_file("lint")}}`

**Must Pass:**
- No correctness-impacting issues (dead code, unused variables that hide mistakes, unsafe patterns)
- Formatting is consistent with repo conventions

### 4. Modern Python Patterns

**Check For:**
- `from __future__ import annotations` at top
- dataclasses for data structures
- Protocol for duck typing
- pathlib.Path for file paths
- Context managers for resources
- Enum for constants

**Anti-Patterns to Flag:**
- `os.path` instead of `pathlib`
- `open()` without context manager
- Mutable default arguments
- Global mutable state

### 5. NO HARDCODING

**Check For:**
- Magic numbers without named constants
- Hardcoded URLs, paths, credentials
- Configuration values in code
- Environment-specific values

**Must Have:**
- Config loaded from YAML files
- Secrets from environment variables only

<!-- /section: PythonChecks -->
