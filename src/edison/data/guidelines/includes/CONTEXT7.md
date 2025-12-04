# Context7 - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- SECTION: workflow -->
## Context7 Workflow (All Roles)

### Purpose
Context7 provides up-to-date documentation for frameworks that may have been updated after AI training data cutoff. **NEVER rely on training data** for frameworks specified in active packs.

### When to Use
- For post-training packages configured in your project
- Check project config for the complete list and supported versions
- When you see deprecation warnings, type errors, or syntax mismatches

### Two-Step Workflow

#### Step 1: Resolve Library ID
```typescript
const pkgId = await mcp__context7__resolve_library_id({ 
  libraryName: '<package-name>' 
})
```

#### Step 2: Query Documentation
```typescript
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: pkgId,
  topic: '<relevant topic>',
  mode: 'code',  // 'code' for API refs, 'info' for concepts
  page: 1
})
```

### Red Flags (Query Immediately)
- Styling not applying because of syntax/version mismatches
- Framework/runtime errors after routing/data API changes
- Type errors from validation/database packages after API shifts
- Deprecation warnings
<!-- /SECTION: workflow -->

<!-- SECTION: agent-markers -->
## Context7 Evidence (Agents)

### Evidence Requirements
When a task uses any package listed in `postTrainingPackages`:

1. **Create marker file** per package in the evidence directory:
   ```
   .project/qa/validation-evidence/<task-id>/round-<N>/context7-<package>.txt
   ```

2. **Include in marker file**:
   - Topics queried
   - Doc version/date
   - HMAC stamp (when enabled in config)

3. **Marker file format**:
   ```
   Package: <package-name>
   Library ID: <resolved-id>
   Topics Queried:
   - <topic-1>
   - <topic-2>
   Documentation Date: <date>
   HMAC: <stamp if enabled>
   ```

### Guards and Enforcement
- Guards block `wip→done` without matching markers
- Notes in task files are NOT accepted as evidence
- `edison task ready` auto-detects post-training packages from git diff
- State machine guards reuse detection results—cannot bypass

### Query Before Implementation
```pseudocode
// BEFORE implementing ANYTHING
framework = identify_framework_from_pack()
docs = await query_context7(framework, topic)
implement_using_current_docs(docs)  // NOT training memory!
```
<!-- /SECTION: agent-markers -->

<!-- SECTION: validator-check -->
## Context7 Validation (Validators)

### Before Validating Code
1. **Refresh your own knowledge** via Context7 BEFORE reviewing
2. Query for packages in active packs
3. Review against CURRENT documentation, not training memory

### Validation Checks
- [ ] Marker files exist for post-training packages used
- [ ] Patterns match current documentation (query to verify)
- [ ] No deprecated patterns from old versions
- [ ] Correct imports/syntax for current framework version

### Red Flags
🚩 **Flag for review:**
- Missing `context7-<pkg>.txt` markers when package is used
- Patterns that look like old framework versions
- Import statements that don't match current docs
- API usage that differs from queried documentation

### Validator Context7 Query Pattern
```pseudocode
// Before flagging ANY code as wrong
framework = identify_framework_from_file_path()
current_docs = await query_context7(framework, pattern_in_question)

// THEN provide feedback based on CURRENT standards
// NEVER flag code as wrong based solely on training data!
```
<!-- /SECTION: validator-check -->
