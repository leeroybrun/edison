# Example 3: Full-Stack Feature (Mixed Implementation)

**Scenario**: Build complete lead notes feature (UI + API + integration)
**Models Used**: Claude Sonnet 4.5 (UI) + Codex (API) - Mixed delegation
**Pattern**: Mixed - sub-agent implements some parts, delegates others

---

## Task Context

**User Request**: "Build a lead notes feature where users can add, edit, and delete notes on lead detail pages. Should support rich text editing and real-time updates."

**Files Involved**:
- `/apps/example-app/src/components/LeadNotes.tsx` (new - UI component)
- `/apps/example-app/src/components/NoteEditor.tsx` (new - UI component)
- `/apps/example-app/src/app/api/v1/resources/leads/[id]/notes/route.ts` (new - API)
- `/apps/example-app/src/app/api/v1/resources/leads/[id]/notes/route.test.ts` (new - Tests)
- `/apps/example-app/src/app/api/v1/resources/leads/[id]/notes/schema.ts` (new - Validation)

**Expected Result**: Complete working feature with UI + backend integration

---

## Step 1: Orchestrator Analysis

### Orchestrator Reads Config

```typescript
// Orchestrator checks task type
const taskType = identifyTaskType(task)
// Result: "full-stack-feature"

// Check taskTypeRules
const rule = config.taskTypeRules['full-stack-feature']
// Result:
{
  "preferredModel": "mixed",
  "subAgentType": "feature-implementer",
  "reason": "UI parts use Claude, backend uses Codex"
}

// Check filePatternRules for specific files
const files = [
  'LeadNotes.tsx',      // *.tsx → claude
  'NoteEditor.tsx',     // *.tsx → claude
  'route.ts',           // **/route.ts → codex
  'route.test.ts',      // **/*.test.ts → codex
  'schema.ts'           // (TypeScript - could be either)
]

// Decision: Delegate to feature-implementer with mixed model guidance
```

### Orchestrator Delegates to Sub-Agent

```typescript
Task({
  subagent_type: 'feature-implementer',
  prompt: `
    Build complete lead notes feature.

    REQUIREMENTS:

    UI Components (2 components):
    1. LeadNotes.tsx
       - Display list of existing notes
       - Add new note button
       - Edit/delete actions per note
       - Loading and error states
       - Real-time updates (refetch after mutations)

    2. NoteEditor.tsx
       - Rich text editor (simple: bold, italic, lists)
       - Save/cancel buttons
       - Character counter (max 1000 chars)
       - Validation errors display

    API Endpoints (1 route file):
    3. /api/v1/resources/leads/[id]/notes
       - GET: List all notes for lead
       - POST: Create new note
       - PATCH: Update existing note
       - DELETE: Delete note
       - Auth: Require OPERATOR role
       - Validation: Zod schema
       - Security: User can only CRUD their own notes

    Testing:
    4. route.test.ts
       - Test all CRUD operations
       - Test authentication/authorization
       - Test validation errors
       - TDD approach

    Validation:
    5. schema.ts
       - Zod schemas for create/update/delete

    FILES:
    - /apps/example-app/src/components/LeadNotes.tsx (UI)
    - /apps/example-app/src/components/NoteEditor.tsx (UI)
    - /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/route.ts (API)
    - /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/route.test.ts (Tests)
    - /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/schema.ts (Validation)

    CONFIG GUIDANCE (CRITICAL - USE MIXED MODEL APPROACH):

    - taskTypeRules['full-stack-feature'] → preferredModel: "mixed"
    - filePatternRules['*.tsx'] → Claude (you implement directly)
    - filePatternRules['**/route.ts'] → Codex (delegate via zen-mcp)
    - filePatternRules['**/*.test.ts'] → Codex (delegate via zen-mcp)

    YOUR DELEGATION STRATEGY:
    1. Implement UI components yourself (LeadNotes.tsx, NoteEditor.tsx)
    2. Delegate API route to Codex (route.ts, route.test.ts, schema.ts)
    3. Verify integration (UI calls API correctly)
    4. Return complete working feature

    Check .edison/delegation/config.json for detailed rules.
  `
})
```

---

## Step 2: Sub-Agent (feature-implementer) Receives Task

### Sub-Agent Reads Config

```typescript
// feature-implementer checks its own defaults
const myDefaults = config.subAgentDefaults['feature-implementer']
// Result:
{
  "defaultModel": "mixed",
  "implementDirectly": "partial",
  "canDelegateTo": ["codex", "gemini"],
  "delegateWhen": "Backend/API files to Codex, UI to self"
}

// Analyze files by pattern
const fileAnalysis = [
  { file: 'LeadNotes.tsx', pattern: '*.tsx', model: 'claude', delegateVia: null },
  { file: 'NoteEditor.tsx', pattern: '*.tsx', model: 'claude', delegateVia: null },
  { file: 'route.ts', pattern: '**/route.ts', model: 'codex', delegateVia: 'zen-mcp' },
  { file: 'route.test.ts', pattern: '**/*.test.ts', model: 'codex', delegateVia: 'zen-mcp' },
  { file: 'schema.ts', pattern: '*.ts', model: 'codex', delegateVia: 'zen-mcp' }  // API-related
]

// Decision Matrix:
// - UI components (2 files): Implement myself (Claude) ✅
// - API route + tests + schema (3 files): Delegate to Codex ✅
// - Integration verification: Do myself after both parts done ✅
//
// FINAL DECISION: Mixed implementation
//   - Part A: Implement UI directly
//   - Part B: Delegate backend to Codex
//   - Part C: Verify integration
```

### Sub-Agent Decision

```
✅ MIXED IMPLEMENTATION

Split Strategy:
1. PART A (Direct Implementation):
   - LeadNotes.tsx → Implement myself (Claude excels at UI/UX)
   - NoteEditor.tsx → Implement myself (Component design is my strength)

2. PART B (Delegation to Codex):
   - route.ts → Delegate to Codex (API precision + security)
   - route.test.ts → Delegate to Codex (Systematic testing)
   - schema.ts → Delegate to Codex (Type safety + validation)

3. PART C (Integration):
   - Verify UI calls API correctly
   - End-to-end test
   - Return complete feature

Proceeding with Part A (UI components)...
```

---

## Step 3A: Sub-Agent Implements UI Components (Direct)

### LeadNotes.tsx (Implemented by feature-implementer)

```typescript
// File: /apps/example-app/src/components/LeadNotes.tsx
// Implemented directly by feature-implementer (Claude)

'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { NoteEditor } from './NoteEditor'

interface Note {
  id: string
  content: string
  createdAt: string
  updatedAt: string
  authorName: string
}

interface LeadNotesProps {
  leadId: string
}

export function LeadNotes({ leadId }: LeadNotesProps) {
  const [isAdding, setIsAdding] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Fetch notes
  const { data: notes = [], isLoading, error } = useQuery<Note[]>({
    queryKey: ['lead-notes', leadId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/resources/leads/${leadId}/notes`)
      if (!response.ok) throw new Error('Failed to fetch notes')
      const data = await response.json()
      return data.notes
    },
  })

  // Create note mutation
  const createMutation = useMutation({
    mutationFn: async (content: string) => {
      const response = await fetch(`/api/v1/resources/leads/${leadId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      if (!response.ok) throw new Error('Failed to create note')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead-notes', leadId] })
      setIsAdding(false)
    },
  })

  // Update note mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, content }: { id: string; content: string }) => {
      const response = await fetch(`/api/v1/resources/leads/${leadId}/notes`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ noteId: id, content }),
      })
      if (!response.ok) throw new Error('Failed to update note')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead-notes', leadId] })
      setEditingId(null)
    },
  })

  // Delete note mutation
  const deleteMutation = useMutation({
    mutationFn: async (noteId: string) => {
      const response = await fetch(`/api/v1/resources/leads/${leadId}/notes`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ noteId }),
      })
      if (!response.ok) throw new Error('Failed to delete note')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead-notes', leadId] })
    },
  })

  if (isLoading) {
    return <div className="text-sm text-[var(--color-text-secondary)]">Loading notes...</div>
  }

  if (error) {
    return (
      <div className="text-sm text-red-600 dark:text-red-400">
        Failed to load notes. Please try again.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
          Notes ({notes.length})
        </h3>
        {!isAdding && (
          <button
            onClick={() => setIsAdding(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            Add Note
          </button>
        )}
      </div>

      {/* Add note editor */}
      {isAdding && (
        <NoteEditor
          onSave={(content) => createMutation.mutate(content)}
          onCancel={() => setIsAdding(false)}
          isLoading={createMutation.isPending}
        />
      )}

      {/* Notes list */}
      <div className="space-y-3">
        {notes.map((note) => (
          <div
            key={note.id}
            className="p-4 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg"
          >
            {editingId === note.id ? (
              <NoteEditor
                initialContent={note.content}
                onSave={(content) => updateMutation.mutate({ id: note.id, content })}
                onCancel={() => setEditingId(null)}
                isLoading={updateMutation.isPending}
              />
            ) : (
              <>
                <div className="prose dark:prose-invert max-w-none mb-3">
                  <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">
                    {note.content}
                  </p>
                </div>
                <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
                  <span>
                    {note.authorName} • {new Date(note.createdAt).toLocaleDateString()}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditingId(note.id)}
                      className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Delete this note?')) {
                          deleteMutation.mutate(note.id)
                        }
                      }}
                      className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        ))}

        {notes.length === 0 && !isAdding && (
          <div className="text-center py-8 text-sm text-[var(--color-text-secondary)]">
            No notes yet. Add your first note to get started.
          </div>
        )}
      </div>
    </div>
  )
}
```

### NoteEditor.tsx (Implemented by feature-implementer)

```typescript
// File: /apps/example-app/src/components/NoteEditor.tsx
// Implemented directly by feature-implementer (Claude)

'use client'

import { useState } from 'react'

interface NoteEditorProps {
  initialContent?: string
  onSave: (content: string) => void
  onCancel: () => void
  isLoading?: boolean
}

export function NoteEditor({
  initialContent = '',
  onSave,
  onCancel,
  isLoading = false,
}: NoteEditorProps) {
  const [content, setContent] = useState(initialContent)
  const [error, setError] = useState<string | null>(null)

  const MAX_LENGTH = 1000

  const handleSave = () => {
    // Validation
    if (!content.trim()) {
      setError('Note cannot be empty')
      return
    }
    if (content.length > MAX_LENGTH) {
      setError(`Note exceeds maximum length of ${MAX_LENGTH} characters`)
      return
    }

    setError(null)
    onSave(content)
  }

  return (
    <div className="space-y-3">
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Write your note here..."
        className="w-full px-4 py-3 bg-[var(--color-input-bg)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        rows={4}
        disabled={isLoading}
      />

      {/* Character counter */}
      <div className="flex items-center justify-between text-xs">
        <span
          className={`${
            content.length > MAX_LENGTH
              ? 'text-red-600 dark:text-red-400'
              : 'text-[var(--color-text-secondary)]'
          }`}
        >
          {content.length} / {MAX_LENGTH} characters
        </span>
      </div>

      {/* Error message */}
      {error && (
        <div className="text-sm text-red-600 dark:text-red-400">{error}</div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={isLoading || !content.trim() || content.length > MAX_LENGTH}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
        >
          {isLoading ? 'Saving...' : 'Save'}
        </button>
        <button
          onClick={onCancel}
          disabled={isLoading}
          className="px-4 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-md hover:bg-[var(--color-surface-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
```

**Part A Complete**: UI components implemented by feature-implementer directly (Claude).

---

## Step 3B: Sub-Agent Delegates Backend to Codex

### Sub-Agent Calls Zen MCP

```typescript
// feature-implementer delegates backend files to Codex
const worktreePath = SessionContext.build_zen_environment(sessionId).ZEN_WORKING_DIR
const result = await mcp__edison-zen__clink({
  cli_name: 'codex',
  role: 'default',
  working_directory: worktreePath,
  prompt: `
    Implement lead notes API endpoints with TDD.

    CONTEXT:
    This is for a nextjs 16 App Router API. UI components already exist (LeadNotes.tsx, NoteEditor.tsx).
    Your job: Implement the backend API that the UI will call.

    REQUIREMENTS:

    1. ROUTE HANDLER (route.ts):
       - Dynamic route: /api/v1/resources/leads/[id]/notes
       - Methods: GET, POST, PATCH, DELETE

       GET /api/v1/resources/leads/[id]/notes:
       - Return all notes for given lead
       - Only notes user has access to (based on role)

       POST /api/v1/resources/leads/[id]/notes:
       - Create new note for lead
       - Body: { content: string }
       - Author: Current authenticated user

       PATCH /api/v1/resources/leads/[id]/notes:
       - Update existing note
       - Body: { noteId: string, content: string }
       - Authorization: User can only update their own notes

       DELETE /api/v1/resources/leads/[id]/notes:
       - Delete note
       - Body: { noteId: string }
       - Authorization: User can only delete their own notes

       Authentication: requireAuth() from @/lib/auth/api-helpers
       Authorization: OPERATOR role required, plus ownership check for PATCH/DELETE

    2. VALIDATION SCHEMA (schema.ts):
       - createNoteSchema: { content: string (min 1, max 1000) }
       - updateNoteSchema: { noteId: string (UUID), content: string (min 1, max 1000) }
       - deleteNoteSchema: { noteId: string (UUID) }

    3. TESTS (route.test.ts):
       - Test GET: Returns notes for lead
       - Test POST: Creates note with auth
       - Test PATCH: Updates own note, rejects others' notes
       - Test DELETE: Deletes own note, rejects others' notes
       - Test auth: 401 without session
       - Test authz: 403 without OPERATOR role
       - Use TDD: Write tests FIRST

    DATABASE:
    Assume LeadNote model exists in prisma schema:
    model LeadNote {
      id String @id @default(uuid())
      leadId String
      lead Lead @relation(fields: [leadId], references: [id])
      content String
      authorId String
      author AppUser @relation(fields: [authorId], references: [id])
      createdAt DateTime @default(now())
      updatedAt DateTime @updatedAt
    }

    FILES TO CREATE:
    - /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/route.ts
    - /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/route.test.ts
    - /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/schema.ts

    SECURITY CHECKLIST:
    - ✅ Authentication (requireAuth)
    - ✅ Authorization (role + ownership)
    - ✅ Input validation (Zod)
    - ✅ No SQL injection (prisma)
    - ✅ Ownership checks (user can only modify own notes)

    Return: All 3 files, tests passing, security verified.
  `,
  absolute_file_paths: [
    '${PROJECT_ROOT}/apps/example-app/src/app/api/v1/resources/[id]/notes/route.ts',
    '${PROJECT_ROOT}/apps/example-app/src/app/api/v1/resources/[id]/notes/route.test.ts',
    '${PROJECT_ROOT}/apps/example-app/src/app/api/v1/resources/[id]/notes/schema.ts'
  ]
})
```

### Codex Implements Backend (Summary)

```
Codex creates 3 files with TDD:

1. schema.ts (30 lines)
   - Zod schemas for create/update/delete
   - Validation rules (max 1000 chars, UUID format, etc.)

2. route.test.ts (400 lines)
   - 15 comprehensive tests
   - Tests all CRUD operations
   - Tests auth/authz
   - Tests ownership checks
   - All tests passing ✅

3. route.ts (250 lines)
   - GET: List notes with author info
   - POST: Create note with auth check
   - PATCH: Update with ownership check
   - DELETE: Delete with ownership check
   - Comprehensive error handling

Security verified: Auth, authz, validation, ownership checks ✅
```

**Part B Complete**: Backend API implemented by Codex via delegation.

---

## Step 3C: Sub-Agent Verifies Integration

### feature-implementer Integration Test

```typescript
// feature-implementer verifies both parts work together

// 1. Check files exist
ls -la /apps/example-app/src/components/LeadNotes.tsx
ls -la /apps/example-app/src/components/NoteEditor.tsx
ls -la /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/
// ✅ All 5 files present

// 2. Run backend tests
npm test route.test.ts
// ✅ 15/15 tests passing (Codex's tests)

// 3. TypeScript compilation
npm run type-check
// ✅ No errors

// 4. Build check
npm run build
// ✅ Build succeeds

// 5. Integration test (manual)
npm run dev

// Navigate to lead detail page
// ✅ LeadNotes component renders
// ✅ "Add Note" button appears
// ✅ Click "Add Note" → NoteEditor appears
// ✅ Type content → Save → API POST call succeeds
// ✅ Note appears in list
// ✅ Click "Edit" → NoteEditor with existing content
// ✅ Modify → Save → API PATCH call succeeds
// ✅ Click "Delete" → Confirm → API DELETE call succeeds
// ✅ Note removed from list

// 6. Network tab verification
// ✅ POST /api/v1/resources/leads/{id}/notes → 201 Created
// ✅ PATCH /api/v1/resources/leads/{id}/notes → 200 OK
// ✅ DELETE /api/v1/resources/leads/{id}/notes → 200 OK
// ✅ GET /api/v1/resources/leads/{id}/notes → 200 OK (refetch after mutations)

// ALL INTEGRATION CHECKS PASS ✅
```

---

## Step 4: Sub-Agent Reports Back to Orchestrator

```
TASK COMPLETE: Lead notes feature (full-stack)

Implementation Approach:
✅ MIXED DELEGATION (optimal strategy)
  - Part A: UI components implemented directly (Claude)
  - Part B: Backend API delegated to Codex (Zen MCP)
  - Part C: Integration verified by feature-implementer

Files Created:
UI (Implemented by feature-implementer - Claude):
- /apps/example-app/src/components/LeadNotes.tsx (180 lines)
- /apps/example-app/src/components/NoteEditor.tsx (120 lines)

Backend (Implemented by Codex):
- /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/route.ts (250 lines)
- /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/route.test.ts (400 lines)
- /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/schema.ts (30 lines)

Total: 980 lines across 5 files

Quality Metrics:
✅ UI Components:
  - React Query for data fetching
  - Optimistic UI updates (real-time feel)
  - Loading/error states
  - Accessible (keyboard nav, ARIA)
  - Theme support (light/dark)

✅ Backend API:
  - TDD (15/15 tests passing)
  - Authentication (Better-Auth)
  - Authorization (role + ownership)
  - Security (validation, no injection)
  - Comprehensive error handling

✅ Integration:
  - UI → API calls work end-to-end
  - Real-time updates after mutations
  - Error handling flows correctly
  - All CRUD operations functional

Test Results:
✅ 15/15 backend tests passing (Codex)
✅ Manual integration tests passing (feature-implementer)

Ready for Integration:
Import: import { LeadNotes } from '@/components/LeadNotes'
Usage: <LeadNotes leadId={lead.id} />
```

---

## Step 5: Orchestrator Verification

```typescript
// Orchestrator final verification

// 1. Files exist
ls -la /apps/example-app/src/components/LeadNotes.tsx
ls -la /apps/example-app/src/components/NoteEditor.tsx
ls -la /apps/example-app/src/app/api/v1/resources/leads/[id]/notes/
// ✅ All 5 files present

// 2. Tests pass
npm test route.test.ts
// ✅ 15/15 passing

// 3. TypeScript compiles
npm run type-check
// ✅ No errors

// 4. Builds
npm run build
// ✅ Build succeeds

// 5. End-to-end test
npm run dev
// Navigate to lead detail, test full CRUD flow
// ✅ Create note → Success
// ✅ Edit note → Success
// ✅ Delete note → Success
// ✅ List updates in real-time
// ✅ Validation works (max chars, empty check)
// ✅ Auth required (logout → 401)

// ALL CHECKS PASS - Task Complete! ✅
```

---

## Key Takeaways

### ✅ Why Mixed Implementation Worked

1. **Task required different expertise**: UI (Claude) + API (Codex)
2. **Config correctly identified mixed strategy**: `preferredModel: "mixed"`
3. **feature-implementer made smart split**:
   - UI to self (Claude's strength)
   - Backend to Codex (Codex's strength)
4. **Integration verified by orchestrator**: feature-implementer ensured parts worked together
5. **Result**: Best of both models, cohesive feature

### 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| **Total time** | ~45 minutes |
| **UI implementation** | ~15 min (Claude direct) |
| **Backend implementation** | ~25 min (Codex via delegation) |
| **Integration verification** | ~5 min (feature-implementer) |
| **Total lines of code** | 980 lines (5 files) |
| **Test coverage** | 100% backend (15 tests) |
| **Security** | Full (auth, authz, ownership) |

### 🎯 Config Usage

**Config sections referenced**:
- ✅ `taskTypeRules['full-stack-feature']` - Identified mixed approach
- ✅ `filePatternRules['*.tsx']` - Claude for UI
- ✅ `filePatternRules['**/route.ts']` - Codex for API
- ✅ `filePatternRules['**/*.test.ts']` - Codex for tests
- ✅ `subAgentDefaults['feature-implementer']` - Confirmed mixed strategy
- ✅ `zenMcpIntegration` - Used to delegate to Codex

**Decision priority**:
1. Task type: full-stack-feature → mixed ✅
2. File patterns: Split by type (UI/API) ✅
3. Sub-agent default: feature-implementer → mixed ✅
4. Sub-agent judgment: Confirmed split was correct ✅

**Result**: Perfect alignment - mixed implementation was optimal strategy.

---

## File-by-File Breakdown

| File | Model | Why |
|------|-------|-----|
| LeadNotes.tsx | Claude | UI component design, UX thinking, React patterns |
| NoteEditor.tsx | Claude | Form handling, validation UX, accessibility |
| route.ts | Codex | API security, precise validation, error handling |
| route.test.ts | Codex | Systematic test coverage, edge cases |
| schema.ts | Codex | Type-safe validation, Zod expertise |

**Rationale**: Each file implemented by model with optimal expertise for that task type.

---

## When to Use Mixed Implementation

✅ **Use mixed implementation when**:
- Task spans UI + backend
- Task type is "full-stack-feature"
- Different files need different expertise
- feature-implementer is the sub-agent
- Config says `preferredModel: "mixed"`

✅ **Split strategy**:
- UI components → Claude (direct)
- API routes → Codex (delegate)
- Database schemas → Codex (delegate)
- Tests → Codex (delegate)
- Integration → feature-implementer verifies

❌ **Don't use mixed when**:
- Task is purely UI (use Claude direct)
- Task is purely backend (delegate fully to Codex)
- Files are all same type (no benefit from splitting)

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────┐
│ USER REQUEST                            │
│ "Build lead notes feature (UI + API)"  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ ORCHESTRATOR                            │
│ 1. Reads config.json                    │
│ 2. taskTypeRules['full-stack'] → mixed │
│ 3. Identifies files: 2 UI + 3 backend  │
│ 4. Selects: feature-implementer        │
│ 5. Suggests: Mixed delegation           │
└──────────────┬──────────────────────────┘
               │
               │ Task(subagent_type='feature-implementer', ...)
               ▼
┌─────────────────────────────────────────┐
│ FEATURE-IMPLEMENTER (Claude)            │
│ 1. Reads config.json                    │
│ 2. Analyzes files by pattern:           │
│    - *.tsx (2 files) → Claude           │
│    - route.ts (3 files) → Codex         │
│ 3. Decision: MIXED implementation       │
└──────────────┬──────────────────────────┘
               │
               ├─── PART A: Implement UI directly
               │    │
               │    ├─ LeadNotes.tsx ✅
               │    └─ NoteEditor.tsx ✅
               │
               └─── PART B: Delegate backend to Codex
                    │
                    │ mcp__edison-zen__clink(codex, working_directory='<session worktree>', ...)
                    ▼
               ┌─────────────────────────────┐
               │ CODEX (via Zen MCP)         │
               │ - route.ts ✅               │
               │ - route.test.ts ✅          │
               │ - schema.ts ✅              │
               └─────────────┬───────────────┘
                             │
                             │ Returns: 3 files, tests passing
                             ▼
               ┌─────────────────────────────┐
               │ FEATURE-IMPLEMENTER         │
               │ PART C: Verify integration  │
               │ - UI calls API ✅           │
               │ - Real-time updates ✅      │
               │ - CRUD works end-to-end ✅  │
               └─────────────┬───────────────┘
                             │
                             │ Complete feature
                             ▼
               ┌─────────────────────────────┐
               │ ORCHESTRATOR                │
               │ Verifies, tests, completes ✅│
               └─────────────────────────────┘
```

---

**Example Type**: Mixed Implementation (Most Complex, Most Realistic)
**Previous Examples**:
- [example-1-ui-component.md](./example-1-ui-component.md) - Direct implementation (Claude only)
- [example-2-api-route.md](./example-2-api-route.md) - Full delegation (Codex only)
