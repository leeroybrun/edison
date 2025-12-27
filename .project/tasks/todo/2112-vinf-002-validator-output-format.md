<!-- TaskID: 2112-vinf-002-validator-output-format -->
<!-- Priority: 2112 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: documentation -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave2-groupB -->
<!-- EstimatedHours: 1 -->

# VINF-002: Create Validator OUTPUT_FORMAT with Tracking Fields

## Summary
Create a validator-specific OUTPUT_FORMAT.md with tracking fields (processId, startedAt, completedAt) that was present in the OLD system but is MISSING from Edison.

## Problem Statement
Current Edison has only an agent OUTPUT_FORMAT. Validators need a specific format including:
- Dual deliverables (markdown + JSON)
- Tracking object with timestamps
- Detailed examples (APPROVED, REJECTED, APPROVED_WITH_WARNINGS)
- Model enforcement section

## Dependencies
- None

## Objectives
- [x] Create validator OUTPUT_FORMAT.md
- [x] Include tracking fields
- [x] Include three detailed examples
- [x] Include CLI I/O policy

## Source Files

### Reference - Old OUTPUT_FORMAT
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/OUTPUT_FORMAT.md
```

### Output Location
```
/Users/leeroy/Documents/Development/edison/src/edison/data/validators/OUTPUT_FORMAT.md
```

## Precise Instructions

### Step 1: Create OUTPUT_FORMAT

Create `/Users/leeroy/Documents/Development/edison/src/edison/data/validators/OUTPUT_FORMAT.md`:

```markdown
# Validator Output Format

Every validator MUST produce TWO outputs:
1. **Markdown Report** - Human-readable summary
2. **JSON Report** - Machine-parseable structured data

Both outputs are required for validation to be complete.

## JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["validator", "status", "tracking", "findings", "summary"],
  "properties": {
    "validator": {
      "type": "string",
      "description": "Validator ID"
    },
    "status": {
      "type": "string",
      "enum": ["APPROVED", "APPROVED_WITH_WARNINGS", "REJECTED"]
    },
    "tracking": {
      "type": "object",
      "required": ["processId", "startedAt", "completedAt"],
      "properties": {
        "processId": {
          "type": "string",
          "format": "uuid",
          "description": "Unique ID for this validation run"
        },
        "startedAt": {
          "type": "string",
          "format": "date-time"
        },
        "completedAt": {
          "type": "string",
          "format": "date-time"
        },
        "durationMs": {
          "type": "integer",
          "description": "Validation duration in milliseconds"
        },
        "model": {
          "type": "string",
          "description": "Model used for validation"
        }
      }
    },
    "filesChecked": {
      "type": "array",
      "items": { "type": "string" }
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["rule", "severity", "file", "message"],
        "properties": {
          "rule": {
            "type": "string",
            "pattern": "^VR-[A-Z]+-\\d{3}$"
          },
          "severity": {
            "type": "string",
            "enum": ["error", "warning", "info"]
          },
          "file": { "type": "string" },
          "line": { "type": "integer" },
          "column": { "type": "integer" },
          "message": { "type": "string" },
          "suggestion": { "type": "string" },
          "evidence": { "type": "string" }
        }
      }
    },
    "summary": {
      "type": "object",
      "required": ["errors", "warnings", "info"],
      "properties": {
        "errors": { "type": "integer", "minimum": 0 },
        "warnings": { "type": "integer", "minimum": 0 },
        "info": { "type": "integer", "minimum": 0 }
      }
    },
    "context7": {
      "type": "object",
      "description": "Context7 usage tracking",
      "properties": {
        "librariesFetched": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  }
}
```

## Tracking Object

The `tracking` object is MANDATORY and auto-populated:

```json
"tracking": {
  "processId": "550e8400-e29b-41d4-a716-446655440000",
  "startedAt": "2025-12-02T10:30:00.000Z",
  "completedAt": "2025-12-02T10:30:45.000Z",
  "durationMs": 45000,
  "model": "codex"
}
```

## Status Determination

```
IF errors > 0:
  status = "REJECTED"
ELSE IF warnings > 0:
  status = "APPROVED_WITH_WARNINGS"
ELSE:
  status = "APPROVED"
```

## Example 1: APPROVED

```json
{
  "validator": "api",
  "status": "APPROVED",
  "tracking": {
    "processId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "startedAt": "2025-12-02T10:00:00.000Z",
    "completedAt": "2025-12-02T10:00:30.000Z",
    "durationMs": 30000,
    "model": "codex"
  },
  "filesChecked": [
    "apps/api/src/routes/leads.ts",
    "apps/api/src/routes/sources.ts"
  ],
  "findings": [],
  "summary": {
    "errors": 0,
    "warnings": 0,
    "info": 0
  },
  "context7": {
    "librariesFetched": ["/fastify/fastify"]
  }
}
```

Markdown:
```markdown
# API Validation Report

**Status**: ✅ APPROVED
**Validator**: api
**Duration**: 30s
**Files**: 2

## Summary
No issues found. All API patterns are correct.

## Files Checked
- apps/api/src/routes/leads.ts
- apps/api/src/routes/sources.ts
```

## Example 2: APPROVED_WITH_WARNINGS

```json
{
  "validator": "react",
  "status": "APPROVED_WITH_WARNINGS",
  "tracking": {
    "processId": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
    "startedAt": "2025-12-02T10:05:00.000Z",
    "completedAt": "2025-12-02T10:05:45.000Z",
    "durationMs": 45000,
    "model": "codex"
  },
  "filesChecked": [
    "apps/dashboard/src/components/Button.tsx"
  ],
  "findings": [
    {
      "rule": "VR-REACT-007",
      "severity": "warning",
      "file": "apps/dashboard/src/components/Button.tsx",
      "line": 15,
      "message": "useMemo used for simple string concatenation",
      "suggestion": "Remove useMemo - primitive concatenation doesn't need memoization"
    },
    {
      "rule": "VR-REACT-012",
      "severity": "info",
      "file": "apps/dashboard/src/components/Button.tsx",
      "line": 8,
      "message": "Consider verifying color contrast meets WCAG AA",
      "suggestion": "Use a contrast checker tool"
    }
  ],
  "summary": {
    "errors": 0,
    "warnings": 1,
    "info": 1
  }
}
```

Markdown:
```markdown
# React Validation Report

**Status**: ⚠️ APPROVED WITH WARNINGS
**Validator**: react
**Duration**: 45s
**Files**: 1

## Summary
1 warning, 1 info. Review recommended before merge.

## Findings

### ⚠️ Warning: VR-REACT-007
**File**: apps/dashboard/src/components/Button.tsx:15
**Message**: useMemo used for simple string concatenation
**Suggestion**: Remove useMemo - primitive concatenation doesn't need memoization

### ℹ️ Info: VR-REACT-012
**File**: apps/dashboard/src/components/Button.tsx:8
**Message**: Consider verifying color contrast meets WCAG AA
**Suggestion**: Use a contrast checker tool
```

## Example 3: REJECTED

```json
{
  "validator": "security",
  "status": "REJECTED",
  "tracking": {
    "processId": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "startedAt": "2025-12-02T10:10:00.000Z",
    "completedAt": "2025-12-02T10:10:20.000Z",
    "durationMs": 20000,
    "model": "codex"
  },
  "filesChecked": [
    "apps/api/src/routes/auth.ts"
  ],
  "findings": [
    {
      "rule": "VR-SEC-001",
      "severity": "error",
      "file": "apps/api/src/routes/auth.ts",
      "line": 42,
      "message": "Password stored in plain text",
      "suggestion": "Use bcrypt or argon2 for password hashing",
      "evidence": "const password = req.body.password; db.insert({ password })"
    },
    {
      "rule": "VR-SEC-003",
      "severity": "error",
      "file": "apps/api/src/routes/auth.ts",
      "line": 58,
      "message": "SQL injection vulnerability",
      "suggestion": "Use parameterized queries",
      "evidence": "db.query(`SELECT * FROM users WHERE id = ${userId}`)"
    }
  ],
  "summary": {
    "errors": 2,
    "warnings": 0,
    "info": 0
  }
}
```

Markdown:
```markdown
# Security Validation Report

**Status**: ❌ REJECTED
**Validator**: security
**Duration**: 20s
**Files**: 1

## Summary
2 critical security errors. MUST FIX before merge.

## Findings

### ❌ Error: VR-SEC-001
**File**: apps/api/src/routes/auth.ts:42
**Message**: Password stored in plain text
**Suggestion**: Use bcrypt or argon2 for password hashing
**Evidence**:
```typescript
const password = req.body.password; db.insert({ password })
```

### ❌ Error: VR-SEC-003
**File**: apps/api/src/routes/auth.ts:58
**Message**: SQL injection vulnerability
**Suggestion**: Use parameterized queries
**Evidence**:
```typescript
db.query(`SELECT * FROM users WHERE id = ${userId}`)
```

## Required Actions
1. Hash passwords before storage
2. Use parameterized queries for all SQL
```

## Model Enforcement

Validators MUST run on their designated model:

| Validator | Required Model |
|-----------|---------------|
| codex-global | codex |
| claude-global | claude |
| gemini-global | gemini |
| security | codex |
| performance | codex |
| api | codex |
| database | codex |
| testing | codex |

Running on wrong model should log warning but not fail.

## CLI I/O Policy

### Input
Validators receive:
- Task ID
- Changed files list
- Context (optional)

```bash
edison validate <task-id>
edison validate <task-id> --files=src/foo.ts,src/bar.ts
edison validate <task-id> --context="Focus on security"
```

### Output
Validators write to:
```
.project/qa/validation-evidence/<task-id>/round-N/
├── <validator-id>.json
├── <validator-id>.md
└── bundle.json (aggregated)
```

### Stdout
Minimal progress updates only:
```
[api] Validating 2 files...
[api] ✓ APPROVED (30s)
```

No verbose output unless `--verbose` flag.
```

## Verification Checklist
- [ ] OUTPUT_FORMAT.md created
- [ ] JSON schema included
- [ ] Tracking object documented
- [ ] Three examples (APPROVED, WITH_WARNINGS, REJECTED)
- [ ] Model enforcement documented
- [ ] CLI I/O policy documented

## Success Criteria
A complete OUTPUT_FORMAT.md exists for validators with tracking fields, examples, and model enforcement.

## Related Issues
- Audit ID: CG-018
- Audit ID: Wave 5 validator findings
