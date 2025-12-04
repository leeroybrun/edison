# Type Safety - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- SECTION: principles -->
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
<!-- /SECTION: principles -->

<!-- SECTION: agent-implementation -->
## Type Safety Implementation (Agents)

### TypeScript Rules
```typescript
// ✅ CORRECT: Explicit types
function processUser(user: User): ProcessedUser {
  return { ...user, processed: true };
}

// ❌ WRONG: any type
function processUser(user: any): any {
  return { ...user, processed: true };
}
```

### Python Rules (mypy strict)
```python
# ✅ CORRECT: Type hints
def process_user(user: User) -> ProcessedUser:
    return ProcessedUser(**user.dict(), processed=True)

# ❌ WRONG: No type hints
def process_user(user):
    return {"processed": True, **user}
```

### Suppression Format
```typescript
// @ts-ignore - Third-party lib XYZ has incorrect types for method foo()
// See: https://github.com/xyz/issues/123
```

```python
# type: ignore[arg-type]  # External API returns untyped dict, validated via Pydantic
```

### Type Checking Commands
```bash
# TypeScript
npx tsc --noEmit

# Python
mypy --strict src/
```
<!-- /SECTION: agent-implementation -->

<!-- SECTION: validator-check -->
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
<!-- /SECTION: validator-check -->
