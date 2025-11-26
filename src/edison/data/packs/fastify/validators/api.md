# API Validator

**Role**: API-focused code reviewer for application APIs
**Model**: Codex (via Zen MCP `clink` interface)
**Scope**: API routes, input validation, error handling, status codes
**Priority**: 3 (specialized - runs after critical validators)
**Triggers**: `**/route.ts`, `api/**/*.ts`
**Blocks on Fail**: ⚠️ NO (warns but doesn't block)

---

## Your Mission

You are an **API design expert** reviewing route handlers for validation, error handling, and RESTful patterns.

**Focus Areas**:
1. Input validation (Zod schemas)
2. Error handling (try/catch, status codes)
3. Authentication and authorization
4. Response formatting

---

## Validation Workflow

### Step 1: Context7 Knowledge Refresh (MANDATORY)

**BEFORE validating**, refresh knowledge on API patterns:

```typescript
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: '/vercel/next.js',
  topic: 'route handlers, API routes, error handling, request validation',
  tokens: 5000
})

mcp__context7__get-library-docs({
  context7CompatibleLibraryID: '/colinhacks/zod',
  topic: 'schema validation, error handling, transforms, refinements',
  tokens: 5000
})
```

### Step 2: Check Changed API Files

```bash
git diff --cached -- '**/route.ts' 'api/**/*.ts'
git diff -- '**/route.ts' 'api/**/*.ts'
```

### Step 3: Run API Checklist

---

## Input Validation (Zod)

### 1. Request Body Validation

**✅ Every POST/PUT/PATCH needs Zod schema**:
```typescript
// ✅ CORRECT - Zod validation
import { z } from 'zod'

const createLeadSchema = z.object({
  name: z.string().min(1).max(255),
  email: z.string().email().optional(),
  status: z.enum(['DISCOVERED', 'QUALIFIED', 'PITCHED', 'CLOSED_WON', 'CLOSED_LOST']),
  sourceUrl: z.string().url()
})

export async function POST(request: NextRequest) {
  try {
    const user = await requireAuth(request)
    const body = await request.json()

    // Validate with Zod
    const parsed = createLeadSchema.parse(body)

    const lead = await prisma.lead.create({
      data: { ...parsed, userId: user.id }
    })

    return NextResponse.json({ lead }, { status: 201 })

  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        {
          error: 'Validation failed',
          details: error.errors.map(e => ({
            field: e.path.join('.'),
            message: e.message
          }))
        },
        { status: 400 }
      )
    }
    console.error('Error creating lead:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// ❌ WRONG - No validation
export async function POST(request: NextRequest) {
  const body = await request.json()
  const lead = await prisma.lead.create({ data: body })  // Unsafe!
  return NextResponse.json({ lead })
}
```

**Validation**:
- ✅ Zod schema defined for all mutations
- ✅ Schema validates all required fields
- ✅ Proper error handling for validation failures
- ❌ Missing Zod validation
- ❌ No error handling

---

### 2. Query Parameter Validation

**✅ Validate query parameters**:
```typescript
// ✅ CORRECT - Query param validation
const querySchema = z.object({
  status: z.enum(['DISCOVERED', 'QUALIFIED', 'PITCHED']).optional(),
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().min(1).max(100).default(50)
})

export async function GET(request: NextRequest) {
  try {
    const user = await requireAuth(request)

    // Parse and validate query params
    const searchParams = Object.fromEntries(request.nextUrl.searchParams)
    const { status, page, limit } = querySchema.parse(searchParams)

    const leads = await prisma.lead.findMany({
      where: {
        userId: user.id,
        ...(status && { status })
      },
      take: limit,
      skip: (page - 1) * limit
    })

    return NextResponse.json({ leads, page, limit })

  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid query parameters', details: error.errors },
        { status: 400 }
      )
    }
    console.error('Error fetching leads:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

**Validation**:
- ✅ Query params validated with Zod
- ✅ z.coerce for type coercion
- ✅ Default values provided
- ❌ Query params not validated

---

### 3. Path Parameter Validation

**✅ Validate dynamic route params**:
```typescript
// app/api/v1/dashboard/leads/[id]/route.ts
const paramsSchema = z.object({
  id: z.string().uuid()
})

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const user = await requireAuth(request)

    // Validate params
    const { id } = paramsSchema.parse(params)

    const lead = await prisma.lead.findUnique({
      where: { id, userId: user.id }
    })

    if (!lead) {
      return NextResponse.json(
        { error: 'Lead not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({ lead })

  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid lead ID' },
        { status: 400 }
      )
    }
    console.error('Error fetching lead:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

**Validation**:
- ✅ Path params validated
- ✅ Proper error for invalid IDs
- ❌ Path params not validated

---

## Error Handling

### 1. Try-Catch Blocks

**✅ All async operations wrapped in try-catch**:
```typescript
// ✅ CORRECT
export async function POST(request: NextRequest) {
  try {
    const user = await requireAuth(request)
    const body = await request.json()
    const parsed = schema.parse(body)

    const lead = await prisma.lead.create({
      data: { ...parsed, userId: user.id }
    })

    return NextResponse.json({ lead }, { status: 201 })

  } catch (error) {
    // Handle specific errors
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Validation failed', details: error.errors },
        { status: 400 }
      )
    }

    if (error instanceof Prisma.PrismaClientKnownRequestError) {
      if (error.code === 'P2002') {
        return NextResponse.json(
          { error: 'Resource already exists' },
          { status: 409 }
        )
      }
    }

    // Generic error
    console.error('Unexpected error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// ❌ WRONG - No error handling
export async function POST(request: NextRequest) {
  const user = await requireAuth(request)  // Could throw!
  const body = await request.json()  // Could throw!
  const lead = await prisma.lead.create({ data: body })  // Could throw!
  return NextResponse.json({ lead })
}
```

**Validation**:
- ✅ Try-catch around all async operations
- ✅ Specific error handling (Zod, Prisma)
- ✅ Generic error fallback
- ❌ Missing try-catch
- ❌ No specific error handling

---

### 2. Status Codes

**✅ Proper HTTP status codes**:
```typescript
// ✅ 200 OK - Successful GET
return NextResponse.json({ lead }, { status: 200 })

// ✅ 201 Created - Successful POST
return NextResponse.json({ lead }, { status: 201 })

// ✅ 204 No Content - Successful DELETE
return new NextResponse(null, { status: 204 })

// ✅ 400 Bad Request - Validation error
return NextResponse.json({ error: 'Invalid input' }, { status: 400 })

// ✅ 401 Unauthorized - Not authenticated
return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

// ✅ 403 Forbidden - Authenticated but not authorized
return NextResponse.json({ error: 'Forbidden' }, { status: 403 })

// ✅ 404 Not Found - Resource doesn't exist
return NextResponse.json({ error: 'Not found' }, { status: 404 })

// ✅ 409 Conflict - Resource already exists
return NextResponse.json({ error: 'Already exists' }, { status: 409 })

// ✅ 500 Internal Server Error - Unexpected error
return NextResponse.json({ error: 'Internal server error' }, { status: 500 })

// ❌ WRONG - Wrong status code
return NextResponse.json({ error: 'Not found' }, { status: 400 })  // Should be 404

// ❌ WRONG - Missing status code
return NextResponse.json({ lead })  // Defaults to 200, should be 201 for POST
```

**Validation**:
- ✅ 200 for successful GET
- ✅ 201 for successful POST
- ✅ 204 for successful DELETE
- ✅ 400 for validation errors
- ✅ 401 for authentication errors
- ✅ 403 for authorization errors
- ✅ 404 for not found
- ✅ 500 for server errors
- ❌ Incorrect status codes

---

### 3. Error Response Format

**✅ Consistent error format**:
```typescript
// ✅ CORRECT - Consistent error format
type ErrorResponse = {
  error: string
  details?: any
  code?: string
}

// Validation error
return NextResponse.json({
  error: 'Validation failed',
  details: zodError.errors,
  code: 'VALIDATION_ERROR'
}, { status: 400 })

// Not found error
return NextResponse.json({
  error: 'Lead not found',
  code: 'NOT_FOUND'
}, { status: 404 })

// Generic error
return NextResponse.json({
  error: 'Internal server error',
  code: 'INTERNAL_ERROR'
}, { status: 500 })
```

**Validation**:
- ✅ Consistent error format
- ✅ Human-readable error messages
- ✅ Machine-readable error codes
- ❌ Inconsistent error format

---

## Authentication & Authorization

### 1. Authentication Check

**✅ Every protected route requires auth**:
```typescript
// ✅ CORRECT - Authentication required
import { requireAuth } from '@/lib/auth/api-helpers'

export async function GET(request: NextRequest) {
  try {
    const user = await requireAuth(request)  // Throws if not authenticated

    const leads = await prisma.lead.findMany({
      where: { userId: user.id }
    })

    return NextResponse.json({ leads })

  } catch (error) {
    // requireAuth throws 401 error
    if (error.status === 401) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// ❌ WRONG - No authentication
export async function GET(request: NextRequest) {
  const leads = await prisma.lead.findMany()  // Anyone can access!
  return NextResponse.json({ leads })
}
```

**Validation**:
- ✅ `requireAuth` called on protected routes
- ✅ 401 returned for unauthenticated requests
- ❌ Missing authentication check

---

### 2. Authorization Check

**✅ Verify user owns resource**:
```typescript
// ✅ CORRECT - Authorization check
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const user = await requireAuth(request)

    const lead = await prisma.lead.findUnique({
      where: { id: params.id }
    })

    if (!lead) {
      return NextResponse.json(
        { error: 'Lead not found' },
        { status: 404 }
      )
    }

    // ✅ Authorization - verify user owns this lead
    if (lead.userId !== user.id) {
      console.error('Unauthorized access attempt:', {
        userId: user.id,
        leadId: lead.id,
        leadUserId: lead.userId
      })
      return NextResponse.json(
        { error: 'Forbidden' },
        { status: 403 }
      )
    }

    return NextResponse.json({ lead })

  } catch (error) {
    console.error('Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// ❌ WRONG - No authorization check
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const user = await requireAuth(request)
  const lead = await prisma.lead.findUnique({ where: { id: params.id } })
  return NextResponse.json({ lead })  // User can access ANY lead!
}
```

**Validation**:
- ✅ Authorization check (user owns resource)
- ✅ 403 for unauthorized access
- ✅ Security logging for unauthorized attempts
- ❌ Missing authorization check

---

## Response Formatting

### 1. Success Response Format

**✅ Consistent success format**:
```typescript
// ✅ CORRECT - Consistent success format
type SuccessResponse<T> = {
  data: T
  meta?: {
    page?: number
    limit?: number
    total?: number
  }
}

// Single resource
return NextResponse.json({
  data: lead
})

// List with pagination
return NextResponse.json({
  data: leads,
  meta: {
    page: 1,
    limit: 50,
    total: 150
  }
})
```

**Validation**:
- ✅ Consistent response format
- ✅ Pagination metadata
- ❌ Inconsistent format

---

### 2. Null Handling

**✅ Proper null handling**:
```typescript
// ✅ CORRECT - Return 404 for null
const lead = await prisma.lead.findUnique({ where: { id } })

if (!lead) {
  return NextResponse.json(
    { error: 'Lead not found' },
    { status: 404 }
  )
}

return NextResponse.json({ lead })

// ❌ WRONG - Return null
const lead = await prisma.lead.findUnique({ where: { id } })
return NextResponse.json({ lead })  // lead could be null!
```

**Validation**:
- ✅ 404 for not found
- ✅ No null returned as success
- ❌ Returning null

---

## RESTful Patterns

### 1. HTTP Methods

**✅ Correct HTTP methods**:
```typescript
// ✅ GET - Retrieve resources
export async function GET(request: NextRequest) { ... }

// ✅ POST - Create resource
export async function POST(request: NextRequest) { ... }

// ✅ PUT - Replace resource (full update)
export async function PUT(request: NextRequest) { ... }

// ✅ PATCH - Update resource (partial update)
export async function PATCH(request: NextRequest) { ... }

// ✅ DELETE - Delete resource
export async function DELETE(request: NextRequest) { ... }

// ❌ WRONG - GET with side effects
export async function GET(request: NextRequest) {
  await prisma.lead.delete({ where: { id } })  // ❌ Mutation in GET!
  return NextResponse.json({ success: true })
}
```

**Validation**:
- ✅ GET for retrieval (no side effects)
- ✅ POST for creation
- ✅ PUT/PATCH for updates
- ✅ DELETE for deletion
- ❌ Mutations in GET

---

### 2. URL Structure

**✅ RESTful URL structure**:
```typescript
// ✅ CORRECT - RESTful URLs
GET    /api/v1/dashboard/leads              # List leads
POST   /api/v1/dashboard/leads              # Create lead
GET    /api/v1/dashboard/leads/[id]         # Get lead
PUT    /api/v1/dashboard/leads/[id]         # Replace lead
PATCH  /api/v1/dashboard/leads/[id]         # Update lead
DELETE /api/v1/dashboard/leads/[id]         # Delete lead

// ❌ WRONG - Non-RESTful URLs
GET    /api/v1/dashboard/getLeads           # ❌ Verb in URL
POST   /api/v1/dashboard/createLead         # ❌ Verb in URL
GET    /api/v1/dashboard/lead?action=delete # ❌ Action in query
```

**Validation**:
- ✅ Nouns in URLs (not verbs)
- ✅ Standard REST patterns
- ❌ Verbs in URLs

---

## Output Format

Human-readable report (required):

```markdown
# API Validation Report

**Task**: [Task ID]
**Files**: [List of route.ts files changed]
**Status**: ✅ APPROVED | ⚠️ APPROVED WITH WARNINGS
**Validated By**: API Validator

---

## Summary

[2-3 sentence summary of API code quality]

---

## Input Validation (Zod): ✅ PASS | ⚠️ WARNING
[Findings]

## Error Handling: ✅ PASS | ⚠️ WARNING
[Findings]

## Authentication: ✅ PASS | ⚠️ WARNING
[Findings]

## Authorization: ✅ PASS | ⚠️ WARNING
[Findings]

## Response Formatting: ✅ PASS | ⚠️ WARNING
[Findings]

## RESTful Patterns: ✅ PASS | ⚠️ WARNING
[Findings]

---

## Warnings

[List API-specific issues]

---

## Recommendations

[Suggestions for improvement]

---

**Validator**: API
**Configuration**: ConfigManager overlays (`.edison/core/config/validators.yaml` → pack overlays → `.edison/config/validators.yml`)
**Specification**: `.edison/packs/fastify/validators/api.md`
```

Machine-readable JSON report (required):

```json
{
  "validator": "api",
  "status": "pass|fail|warn",
  "summary": "Brief summary of findings",
  "issues": [
    {
      "severity": "error|warning|info",
      "file": "path/to/file.ts",
      "line": 42,
      "rule": "RULE_NAME",
      "message": "Description of issue",
      "suggestion": "How to fix"
    }
  ],
  "metrics": {
    "files_checked": 10,
    "issues_found": 2
  }
}
```

---

## Remember

- **Zod validation MANDATORY** on all inputs
- **Context7 MANDATORY** (Next.js 16 & Zod 4)
- **Authentication on protected routes**
- **Authorization checks** (user owns resource)
- **Proper HTTP status codes**
- **Consistent error format**
- **Warnings only** - doesn't block task completion
