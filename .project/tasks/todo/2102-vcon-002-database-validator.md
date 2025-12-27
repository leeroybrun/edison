<!-- TaskID: 2102-vcon-002-database-validator -->
<!-- Priority: 2102 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: feature -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave2-groupA -->
<!-- EstimatedHours: 4 -->
<!-- DependsOn: 2003-efix-003, 2004-efix-004 -->

# VCON-002: Create database.md Validator Constitution

## Summary
Create a complete database validator constitution based on the OLD system's 675-line database.md validator. This specialized validator checks database schema design, migrations, and query patterns.

## Problem Statement
The OLD system had a comprehensive database.md validator (675 lines) that is MISSING from Edison. This validator enforced:
- Schema design best practices
- Migration safety
- Index optimization
- Relationship integrity
- Query performance patterns

## Dependencies
- EFIX-003 (rules composition) - helpful but not blocking

## Objectives
- [x] Create complete database.md validator
- [x] Include all validation rules from OLD system
- [x] Add Prisma-specific patterns
- [x] Ensure composability (core + prisma pack + overlay)

## Source Files

### Reference - Old Validator
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/database.md
```

### Output Location
```
/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/database.md
```

## Precise Instructions

### Step 1: Analyze Old Validator
```bash
cat /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/database.md | head -100
wc -l /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/database.md
```

### Step 2: Create Core Validator

Create `/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/database.md`:

```markdown
---
id: database
type: specialized
model: codex
triggers:
  - "schema.prisma"
  - "**/prisma/**/*"
  - "**/*.sql"
  - "**/migrations/**/*"
blocksOnFail: true
---

# Database Validator

**Type**: Specialized Validator
**Triggers**: Schema and migration files
**Blocking**: Yes (critical for data integrity)

## Constitution Awareness

**Role Type**: VALIDATOR
**Constitution**: `.edison/_generated/constitutions/VALIDATORS.md`

### Binding Rules
1. **Re-read Constitution**: At validation start
2. **Authority**: Constitution > Validator Guidelines > Task Context
3. **Role Boundaries**: You VALIDATE database designs. You do NOT implement fixes.
4. **Output**: APPROVED, APPROVED_WITH_WARNINGS, or REJECTED with evidence

## Validation Scope

This validator checks database implementations for:
1. Schema design quality
2. Migration safety
3. Index optimization
4. Relationship integrity
5. Naming conventions
6. Data type appropriateness
7. Performance implications

## Validation Rules

### VR-DB-001: Primary Key Presence
**Severity**: Error
**Check**: Every table has a primary key

Verify:
- All models have `@id` field
- ID type is appropriate (UUID preferred)
- No composite keys without justification

**Fail Condition**: Model without primary key

### VR-DB-002: Relationship Integrity
**Severity**: Error
**Check**: Foreign key relationships are properly defined

Verify:
- Relations have both sides defined
- Cascade behaviors specified
- No orphan references possible

**Fail Condition**: Incomplete relationship definition

### VR-DB-003: Index Optimization
**Severity**: Warning
**Check**: Frequently queried fields are indexed

Patterns to verify:
- Foreign keys have indexes
- Fields used in WHERE clauses indexed
- Composite indexes for multi-column queries
- No over-indexing (write performance)

**Fail Condition**: Missing obvious indexes

### VR-DB-004: Migration Safety
**Severity**: Error
**Check**: Migrations are safe to run

Dangerous patterns:
- Dropping columns with data
- Changing column types with data loss
- Removing NOT NULL without default
- Large table alterations without batching

**Fail Condition**: Destructive migration without safety measures

### VR-DB-005: Naming Conventions
**Severity**: Warning
**Check**: Names follow conventions

Expected patterns:
- Tables: PascalCase (Prisma) or snake_case (SQL)
- Columns: camelCase (Prisma) or snake_case (SQL)
- Indexes: idx_{table}_{columns}
- Foreign keys: fk_{table}_{ref_table}

**Fail Condition**: Inconsistent naming

### VR-DB-006: Data Type Appropriateness
**Severity**: Warning
**Check**: Data types match use case

Common issues:
- String for numeric data
- Float for monetary values (use Decimal)
- Unbounded strings for fixed-length data
- DateTime without timezone

**Fail Condition**: Inappropriate data type

### VR-DB-007: Enum Usage
**Severity**: Info
**Check**: Enums used appropriately

Verify:
- Fixed value sets use enums
- Enums are not overused for dynamic data
- Enum values are descriptive

**Fail Condition**: String used for fixed value set

### VR-DB-008: Soft Delete Pattern
**Severity**: Info
**Check**: Deletion strategy is intentional

Patterns:
- Hard delete (actual removal)
- Soft delete (deletedAt timestamp)
- Archive pattern (move to archive table)

**Fail Condition**: No clear deletion strategy

### VR-DB-009: Audit Fields
**Severity**: Warning
**Check**: Tables have audit fields

Expected fields:
- `createdAt DateTime @default(now())`
- `updatedAt DateTime @updatedAt`
- `createdBy` (optional)
- `updatedBy` (optional)

**Fail Condition**: Missing createdAt/updatedAt

### VR-DB-010: Query Performance
**Severity**: Warning
**Check**: Queries are optimized

Patterns to avoid:
- SELECT * in production code
- N+1 query patterns
- Missing eager loading
- Unbounded queries without pagination

**Fail Condition**: Obvious performance anti-pattern

## Migration Validation

### VR-MIG-001: Reversibility
**Severity**: Warning
**Check**: Migrations have down migrations

Verify:
- Down migration exists
- Down migration is tested
- Data preservation where possible

### VR-MIG-002: Deployment Safety
**Severity**: Error
**Check**: Migration is deployment-safe

Dangerous patterns:
- Long-running locks
- Schema changes that break running app
- Missing transactions

### VR-MIG-003: Data Migration
**Severity**: Warning
**Check**: Data migrations are separate

Pattern:
- Schema migrations: DDL only
- Data migrations: Separate scripts
- Never mix DDL and DML

## Output Format

```json
{
  "validator": "database",
  "status": "APPROVED" | "APPROVED_WITH_WARNINGS" | "REJECTED",
  "filesChecked": ["prisma/schema.prisma"],
  "findings": [
    {
      "rule": "VR-DB-003",
      "severity": "warning",
      "file": "prisma/schema.prisma",
      "line": 42,
      "message": "Field 'email' used in queries but not indexed",
      "suggestion": "Add @@index([email]) to User model"
    }
  ],
  "summary": {
    "errors": 0,
    "warnings": 1,
    "info": 0
  }
}
```

## Context7 Requirements

```
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/prisma/prisma",
  topic: "schema"
})
```
```

### Step 3: Add Prisma Pack Extensions

The prisma pack should add Prisma-specific rules. Check if exists:
```bash
ls /Users/leeroy/Documents/Development/edison/src/edison/packs/prisma/validators/
```

### Step 4: Verify Composition
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose validators
cat .edison/_generated/validators/specialized/database.md | head -50
```

## Verification Checklist
- [ ] Core validator created at Edison path
- [ ] Contains all VR-DB and VR-MIG rules
- [ ] Prisma-specific patterns included
- [ ] Composition produces complete validator
- [ ] JSON output format documented
- [ ] blocksOnFail is true (critical)

## Success Criteria
A complete database validator exists that catches schema design issues, migration safety problems, and query anti-patterns.

## Related Issues
- Audit ID: Wave 5 validator findings
