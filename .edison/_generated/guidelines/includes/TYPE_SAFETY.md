# Type Safety - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: principles -->
## Type Safety Principles (All Roles)

### Core Rules
- Type safety settings are defined by project configuration
- No type suppressions without explanation
- Public interfaces/contracts should be typed as applicable for the language/tooling

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
- [ ] No type-system escape hatches without justification
- [ ] No ignore/suppression directives without an explicit rationale
- [ ] All suppressions have explanatory comments
- [ ] Public-facing interfaces/contracts are fully typed (as applicable)

### Red Flags
🚩 **Immediate rejection:**
- Type-system escape hatches without comment/rationale
- Bare suppressions without explanation
- Project type-safety settings disabled without explicit approval
- Type errors ignored in CI

🟡 **Needs review:**
- Many type assertions (`as Type`)
- Complex generic constraints
- Frequent use of `unknown`
<!-- /section: validator-check -->