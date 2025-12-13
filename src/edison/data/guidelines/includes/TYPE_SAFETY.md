# Type Safety - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: principles -->
## Type Safety Principles (All Roles)

### Core Rules
- Strict typing enabled in all projects
- No `any` type without documented justification
- No type suppressions without explanation
- All function parameters and return types explicit

### Benefits
- Catch bugs at compile time, not runtime
- Self-documenting code
- Safer refactoring
- Better IDE support

### Allowed Exceptions
Type suppressions are allowed ONLY when:
1. Third-party library has incorrect types
2. Temporary workaround with linked issue
3. Complex generic constraints (documented)

Every suppression requires a comment explaining why.
<!-- /section: principles -->

<!-- section: agent-implementation -->
## Type Safety Implementation (Agents)

### Rules
- Prefer explicit types over inference when it improves clarity
- Avoid “escape hatch” types (e.g., dynamic/untyped) unless justified
- If you must suppress a type error, include a comment explaining **why** and **how it’s safe**

### Example (Pseudocode)
```pseudocode
// ✅ CORRECT: explicit input/output types
function process_user(user: User) -> ProcessedUser:
  return ProcessedUser(user, processed=true)

// ❌ WRONG: untyped inputs/outputs (hard to validate/refactor)
function process_user(user):
  return { processed: true, ...user }
```

### Type Checking Command
```bash
<type-check-command>
```
<!-- /section: agent-implementation -->

<!-- section: validator-check -->
## Type Safety Validation (Validators)

### Checklist
- [ ] Type checking passes with zero errors
- [ ] No `any` types without justification comment
- [ ] No bare `@ts-ignore` or `# type: ignore`
- [ ] All suppressions have explanatory comments
- [ ] Function signatures are fully typed
- [ ] Return types are explicit

### Red Flags
🚩 **Immediate rejection:**
- `any` used as escape hatch without comment
- Bare suppressions without explanation
- Strict mode disabled
- Type errors ignored in CI

🟡 **Needs review:**
- Many type assertions (`as Type`)
- Complex generic constraints
- Frequent use of `unknown`
<!-- /section: validator-check -->
