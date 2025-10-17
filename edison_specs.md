# Edison v1 - Complete Technical Specification

## **Document Control**

**Version:** 1.0.0  
**Last Updated:** 2025-10-17  
**Status:** Final  
**Target Audience:** Engineering Team, Product Managers, QA Engineers, UX Designers

-----

# **Table of Contents**

1. [Executive Summary](#1-executive-summary)
1. [System Overview](#2-system-overview)
1. [Functional Requirements](#3-functional-requirements)
1. [Non-Functional Requirements](#4-non-functional-requirements)
1. [User Flows & Journeys](#5-user-flows--journeys)
1. [UI/UX Specifications](#6-uiux-specifications)
1. [API Specifications](#7-api-specifications)
1. [Data Model Specifications](#8-data-model-specifications)
1. [Business Logic Rules](#9-business-logic-rules)
1. [LLM Integration Specifications](#10-llm-integration-specifications)
1. [Security Specifications](#11-security-specifications)
1. [Performance Requirements](#12-performance-requirements)
1. [Error Handling & Recovery](#13-error-handling--recovery)
1. [Testing Requirements](#14-testing-requirements)
1. [Deployment Specifications](#15-deployment-specifications)
1. [Monitoring & Observability](#16-monitoring--observability)
1. [Accessibility Requirements](#17-accessibility-requirements)
1. [Internationalization](#18-internationalization)
1. [Edge Cases & Corner Cases](#19-edge-cases--corner-cases)
1. [Migration & Upgrade Paths](#20-migration--upgrade-paths)

-----

# **1. Executive Summary**

## **1.1 Product Vision**

Edison is a self-hosted prompt engineering workbench that enables teams to design, test, and optimize AI prompts through an iterative, human-in-the-loop process with AI assistance. It combines manual craftsmanship with automated evaluation and refinement to produce production-ready prompts.

## **1.2 Core Value Proposition**

- **Speed**: Reduce prompt development from weeks to days through AI-assisted authoring
- **Quality**: Multi-model evaluation with statistical rigor ensures robust prompts
- **Transparency**: Diff-based refinement shows exactly what changed and why
- **Control**: Human approval gates prevent unwanted changes
- **Cost-Effectiveness**: Budget controls and early stopping prevent runaway spending

## **1.3 Success Metrics**

|Metric                                  |Target              |Measurement Method       |
|----------------------------------------|--------------------|-------------------------|
|Time to first working prompt            |< 30 minutes        |User onboarding telemetry|
|Prompt quality improvement per iteration|> 5% composite score|Iteration metrics        |
|User satisfaction (NPS)                 |> 50                |Quarterly surveys        |
|System uptime                           |99.5%               |Monitoring alerts        |
|API response time (p95)                 |< 500ms             |APM tooling              |
|Cost per experiment                     |< $10 average       |Usage analytics          |

## **1.4 Out of Scope (v1)**

- ❌ Multi-tenant SaaS deployment
- ❌ Real-time collaboration (simultaneous editing)
- ❌ Production deployment/serving infrastructure
- ❌ A/B testing framework
- ❌ Custom model fine-tuning
- ❌ Mobile native apps
- ❌ Plugin/extension system
- ❌ White-label/reseller capabilities

-----

# **2. System Overview**

## **2.1 Architecture Diagram**

```
┌──────────────────────────────────────────────────────────────────┐
│                          User Browser                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  React UI  │  │   Charts   │  │  Real-time │                │
│  │ Components │  │  (Recharts)│  │    SSE     │                │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                │
│        │                │                │                        │
└────────┼────────────────┼────────────────┼────────────────────────┘
         │                │                │
         │ tRPC           │ HTTP           │ EventSource
         │                │                │
┌────────▼────────────────▼────────────────▼────────────────────────┐
│                      Next.js 14 App Router                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐│
│  │  Server          │  │  API Routes      │  │  SSE Endpoints  ││
│  │  Components      │  │  (tRPC)          │  │  (/api/stream)  ││
│  └──────────────────┘  └──────────────────┘  └─────────────────┘│
└────────┬──────────────────────┬──────────────────────┬───────────┘
         │                      │                      │
         │ Import               │ Import               │ Import
         │                      │                      │
┌────────▼──────────────────────▼──────────────────────▼───────────┐
│                         Hono API Server                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      tRPC Router                             │ │
│  │  • ProjectRouter  • ExperimentRouter  • PromptRouter        │ │
│  │  • DatasetRouter  • RunRouter         • ReviewRouter        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     Service Layer                            │ │
│  │  • Orchestrator     • Evaluator      • Aggregator           │ │
│  │  • Refiner          • Generator      • BudgetEnforcer       │ │
│  │  • AIAssist         • SafetyChecker  • CoverageAnalyzer     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   LLM Adapter Layer                          │ │
│  │  • OpenAIAdapter    • AnthropicAdapter                       │ │
│  │  • VertexAdapter    • BedrockAdapter                         │ │
│  │  • AzureAdapter     • OllamaAdapter                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
└────────┬────────────────────────┬──────────────────────┬─────────┘
         │                        │                      │
         │ Read/Write             │ Enqueue              │ Publish
         │                        │                      │
┌────────▼───────┐   ┌────────────▼─────────┐   ┌──────▼──────────┐
│   PostgreSQL   │   │    Redis (BullMQ)    │   │  Redis PubSub   │
│   (Prisma)     │   │   Job Queues:        │   │  (SSE Events)   │
│                │   │   • execute-run      │   │                 │
│   • Projects   │   │   • judge-outputs    │   │                 │
│   • Experiments│   │   • aggregate-scores │   │                 │
│   • Prompts    │   │   • refine-prompt    │   │                 │
│   • Runs       │   │   • generate-dataset │   │                 │
│   • Judgments  │   │   • safety-scan      │   │                 │
│   • ...        │   └──────────┬───────────┘   └─────────────────┘
└────────────────┘              │
                                │ Dequeue
                   ┌────────────▼────────────┐
                   │   BullMQ Workers        │
                   │   (Multiple Processes)  │
                   │                         │
                   │   • ExecuteWorker       │
                   │   • JudgeWorker         │
                   │   • AggregateWorker     │
                   │   • RefineWorker        │
                   │   • GenerateWorker      │
                   └─────────────────────────┘
```

## **2.2 Technology Stack**

### **Frontend**

|Component    |Technology     |Version|Purpose                            |
|-------------|---------------|-------|-----------------------------------|
|Framework    |Next.js        |14.2+  |React metaframework with App Router|
|UI Library   |React          |18.2+  |Component library                  |
|Language     |TypeScript     |5.3+   |Type safety                        |
|Styling      |Tailwind CSS   |3.4+   |Utility-first CSS                  |
|Components   |shadcn/ui      |latest |Accessible component primitives    |
|Icons        |Lucide React   |0.400+ |Icon library                       |
|Forms        |React Hook Form|7.51+  |Form state management              |
|Validation   |Zod            |3.22+  |Schema validation                  |
|State        |Zustand        |4.5+   |Lightweight state management       |
|Server State |TanStack Query |5.28+  |Async state management             |
|RPC          |tRPC           |10.45+ |End-to-end type safety             |
|Charts       |Recharts       |2.12+  |Composable charting                |
|Animation    |Framer Motion  |11.0+  |Animation library                  |
|Code Editor  |Monaco Editor  |0.47+  |Code editing component             |
|Diff Viewer  |react-diff-view|3.2+   |Diff visualization                 |
|Date Handling|date-fns       |3.3+   |Date utilities                     |
|Markdown     |react-markdown |9.0+   |Markdown rendering                 |

### **Backend**

|Component  |Technology   |Version|Purpose             |
|-----------|-------------|-------|--------------------|
|Runtime    |Node.js      |20+    |JavaScript runtime  |
|Framework  |Hono         |4.0+   |Fast web framework  |
|Language   |TypeScript   |5.3+   |Type safety         |
|ORM        |Prisma       |5.11+  |Database toolkit    |
|Database   |PostgreSQL   |16+    |Relational database |
|Cache/Queue|Redis        |7.2+   |In-memory data store|
|Job Queue  |BullMQ       |5.4+   |Job queue library   |
|Validation |Zod          |3.22+  |Schema validation   |
|Crypto     |libsodium    |0.7+   |Encryption library  |
|Auth       |jsonwebtoken |9.0+   |JWT handling        |
|Password   |bcrypt       |5.1+   |Password hashing    |
|Logging    |Pino         |8.19+  |Fast JSON logger    |
|Tracing    |OpenTelemetry|1.21+  |Distributed tracing |
|Testing    |Vitest       |1.4+   |Unit test framework |

### **LLM SDKs**

|Provider |SDK                            |Version|Purpose                  |
|---------|-------------------------------|-------|-------------------------|
|OpenAI   |openai                         |4.28+  |OpenAI API client        |
|Anthropic|@anthropic-ai/sdk              |0.20+  |Anthropic API client     |
|Google   |@google-cloud/aiplatform       |3.18+  |Vertex AI client         |
|AWS      |@aws-sdk/client-bedrock-runtime|3.540+ |Bedrock client           |
|Vercel   |ai                             |3.0+   |Unified AI SDK (optional)|

### **DevOps**

|Component    |Technology    |Version|Purpose               |
|-------------|--------------|-------|----------------------|
|Container    |Docker        |24+    |Containerization      |
|Orchestration|Docker Compose|2.24+  |Local orchestration   |
|CI/CD        |GitHub Actions|-      |Continuous integration|
|E2E Testing  |Playwright    |1.42+  |Browser automation    |
|Code Quality |ESLint        |8.57+  |Linting               |
|Formatting   |Prettier      |3.2+   |Code formatting       |

## **2.3 System Context**

### **External Systems**

```
┌─────────────────────────────────────────────────────────────────┐
│                      External Systems                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │   OpenAI     │   │  Anthropic   │   │  Google      │       │
│  │     API      │   │     API      │   │  Vertex AI   │       │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘       │
│         │                   │                   │               │
│         │ HTTPS/JSON        │ HTTPS/JSON        │ gRPC         │
│         │                   │                   │               │
└─────────┼───────────────────┼───────────────────┼───────────────┘
          │                   │                   │
          └───────────────────┴───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Edison System   │
                    │   (Self-hosted)   │
                    └───────────────────┘
```

### **Integration Points**

1. **LLM Provider APIs**: RESTful/gRPC calls for chat completions
1. **User Authentication**: JWT-based auth (no external IdP in v1)
1. **File Storage**: Local filesystem (no S3/cloud storage in v1)
1. **Email Notifications**: SMTP for async notifications (optional)
1. **Metrics Export**: OpenTelemetry-compatible backends (optional)

-----

# **3. Functional Requirements**

## **3.1 User Management**

### **FR-UM-001: User Registration**

**Priority:** P0 (Must Have)  
**User Story:** As a new user, I want to create an account so that I can access Edison.

**Acceptance Criteria:**

- User can register with email and password
- Email must be valid format (RFC 5322 compliant)
- Password must meet complexity requirements:
  - Minimum 12 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number
  - At least 1 special character (!@#$%^&*)
- Email must be unique across all users
- User receives confirmation of account creation
- Account is immediately active (no email verification in v1)

**Validation Rules:**

```typescript
const registerSchema = z.object({
  email: z.string().email().max(255),
  name: z.string().min(1).max(255).optional(),
  password: z.string()
    .min(12, 'Password must be at least 12 characters')
    .regex(/[A-Z]/, 'Must contain uppercase letter')
    .regex(/[a-z]/, 'Must contain lowercase letter')
    .regex(/[0-9]/, 'Must contain number')
    .regex(/[!@#$%^&*]/, 'Must contain special character'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});
```

**Error Cases:**

- `EMAIL_TAKEN`: Email already registered → Show “Email already in use”
- `WEAK_PASSWORD`: Password doesn’t meet requirements → Show specific requirement violated
- `INVALID_EMAIL`: Malformed email → Show “Invalid email format”
- `RATE_LIMIT`: Too many registration attempts → Show “Too many attempts, try again in 15 minutes”

**UI Mockup Description:**

- Center-aligned card (max-width: 400px)
- Logo at top
- Title: “Create your account”
- Fields:
  - Full Name (optional, single line input)
  - Email (required, type=“email”)
  - Password (required, type=“password”, show/hide toggle)
  - Confirm Password (required, type=“password”)
- Password strength indicator (weak/fair/good/strong)
- Submit button: “Create account” (primary, full width)
- Link to login: “Already have an account? Sign in”
- Terms acceptance checkbox: “I agree to Terms of Service”

### **FR-UM-002: User Login**

**Priority:** P0 (Must Have)  
**User Story:** As a registered user, I want to log in so that I can access my projects.

**Acceptance Criteria:**

- User can log in with email and password
- Successful login returns JWT token (expires in 7 days)
- Token includes claims: userId, email, role
- Failed login shows clear error message
- After 5 failed attempts, account is locked for 15 minutes
- “Remember me” checkbox extends token to 30 days

**Validation Rules:**

```typescript
const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  rememberMe: z.boolean().default(false),
});
```

**Security Requirements:**

- Passwords hashed with bcrypt (cost factor: 12)
- Rate limiting: 5 attempts per 15 minutes per IP
- Failed login attempts logged to audit log
- No timing attacks (constant-time comparison)

**Error Cases:**

- `INVALID_CREDENTIALS`: Email or password incorrect → Show “Invalid email or password” (never reveal which)
- `ACCOUNT_LOCKED`: Too many failed attempts → Show “Account temporarily locked. Try again in X minutes”
- `RATE_LIMIT`: Too many requests → Show “Too many login attempts. Please wait.”

### **FR-UM-003: User Roles & Permissions**

**Priority:** P0 (Must Have)  
**User Story:** As a project owner, I want to control who can view, edit, or manage my projects.

**Role Definitions:**

|Role        |Capabilities                                                                                                                             |
|------------|-----------------------------------------------------------------------------------------------------------------------------------------|
|**VIEWER**  |• View experiments<br>• View runs<br>• View datasets<br>• Export results<br>❌ Cannot create/edit                                         |
|**REVIEWER**|All VIEWER permissions, plus:<br>• Review suggestions (approve/reject)<br>• Add comments<br>❌ Cannot create experiments                  |
|**EDITOR**  |All REVIEWER permissions, plus:<br>• Create experiments<br>• Edit prompts<br>• Upload datasets<br>• Start runs<br>❌ Cannot manage members|
|**ADMIN**   |All EDITOR permissions, plus:<br>• Manage project settings<br>• Add/remove members<br>• Manage API credentials<br>❌ Cannot delete project|
|**OWNER**   |All ADMIN permissions, plus:<br>• Delete project<br>• Transfer ownership<br>• Manage billing (future)                                    |

**Permission Enforcement:**

- Permissions checked at API layer (tRPC middleware)
- Permissions checked at database layer (row-level)
- UI elements hidden based on permissions (never rely solely on this)
- All permission checks logged to audit log

**Permission Check Examples:**

```typescript
// Can user edit experiment?
const canEditExperiment = await prisma.projectMember.findFirst({
  where: {
    projectId: experiment.projectId,
    userId: currentUser.id,
    role: { in: ['EDITOR', 'ADMIN', 'OWNER'] },
  },
});

if (!canEditExperiment) {
  throw new TRPCError({ code: 'FORBIDDEN' });
}
```

### **FR-UM-004: Session Management**

**Priority:** P0 (Must Have)

**Requirements:**

- JWT tokens stored in HTTP-only cookies
- Tokens auto-refresh 1 day before expiry
- Logout clears token and redirects to login
- Expired tokens trigger automatic logout
- Concurrent sessions allowed (no limit in v1)

**Token Structure:**

```typescript
interface JWTPayload {
  sub: string;        // userId
  email: string;
  role: UserRole;
  iat: number;        // issued at
  exp: number;        // expires at
  jti: string;        // unique token ID
}
```

-----

## **3.2 Project Management**

### **FR-PM-001: Create Project**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to create a project to organize my prompt engineering work.

**Acceptance Criteria:**

- User can create project with name and optional description
- Project slug auto-generated from name (kebab-case, unique)
- User who creates project is automatically OWNER
- Project can have settings: default model, default budget, etc.
- Project creation is atomic (all-or-nothing)

**Validation Rules:**

```typescript
const createProjectSchema = z.object({
  name: z.string()
    .min(1, 'Name is required')
    .max(100, 'Name too long')
    .regex(/^[a-zA-Z0-9\s\-_]+$/, 'Only alphanumeric, spaces, hyphens, underscores'),
  description: z.string().max(1000).optional(),
  settings: z.object({
    defaultProvider: z.enum(['OPENAI', 'ANTHROPIC']).optional(),
    defaultBudgetUsd: z.number().min(0).max(10000).optional(),
    defaultMaxIterations: z.number().int().min(1).max(100).default(10),
  }).optional(),
});
```

**Slug Generation Logic:**

```typescript
function generateSlug(name: string, existingSlugs: string[]): string {
  let baseSlug = name
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .substring(0, 50);
  
  let slug = baseSlug;
  let counter = 1;
  
  while (existingSlugs.includes(slug)) {
    slug = `${baseSlug}-${counter}`;
    counter++;
  }
  
  return slug;
}
```

**Post-Creation Actions:**

- Create default “Golden” dataset
- Log creation to audit log
- Show success toast
- Redirect to project dashboard

### **FR-PM-002: List Projects**

**Priority:** P0 (Must Have)

**Acceptance Criteria:**

- User sees all projects they’re a member of
- Projects sorted by last updated (most recent first)
- Each project card shows:
  - Project name
  - Description (truncated to 100 chars)
  - Last updated timestamp (relative: “2 hours ago”)
  - Member count
  - Experiment count
  - User’s role badge
- Pagination: 20 projects per page
- Search by name (debounced, min 2 chars)
- Filter by role (dropdown: All, Owner, Admin, Editor, Reviewer, Viewer)

**Query Optimization:**

```sql
-- Efficient query with counts
SELECT 
  p.*,
  pm.role as user_role,
  COUNT(DISTINCT e.id) as experiment_count,
  COUNT(DISTINCT pm2.id) as member_count
FROM projects p
INNER JOIN project_members pm ON p.id = pm.project_id
LEFT JOIN experiments e ON p.id = e.project_id
LEFT JOIN project_members pm2 ON p.id = pm2.project_id
WHERE pm.user_id = $1
  AND ($2::text IS NULL OR p.name ILIKE $2)
  AND ($3::user_role IS NULL OR pm.role = $3)
GROUP BY p.id, pm.role
ORDER BY p.updated_at DESC
LIMIT 20 OFFSET $4;
```

### **FR-PM-003: Project Settings**

**Priority:** P1 (Should Have)

**Configurable Settings:**

|Setting                 |Type   |Default|Description                              |
|------------------------|-------|-------|-----------------------------------------|
|`defaultProvider`       |enum   |OPENAI |Default LLM provider                     |
|`defaultBudgetUsd`      |number |100    |Default per-experiment budget            |
|`defaultMaxIterations`  |number |10     |Default max iterations                   |
|`allowSyntheticDatasets`|boolean|true   |Enable dataset generation                |
|`requireReviewApproval` |boolean|true   |Require HITL approval for all refinements|
|`costAlertThreshold`    |number |0.8    |Alert when 80% of budget used            |
|`retentionDays`         |number |90     |Delete old runs after N days (0 = never) |

**Permission:** Only ADMIN and OWNER can edit settings.

### **FR-PM-004: Manage Project Members**

**Priority:** P1 (Should Have)

**Acceptance Criteria:**

- ADMIN/OWNER can invite users by email
- Invitee receives email with accept link (if email configured)
- If no email, show invite link to copy/paste
- ADMIN/OWNER can change member roles
- ADMIN/OWNER can remove members
- OWNER can transfer ownership
- Cannot remove last OWNER

**Invite Flow:**

1. Enter email address
1. Select role (VIEWER to ADMIN)
1. Optional personal message
1. Click “Send Invite”
1. If user exists: Add to project immediately
1. If user doesn’t exist: Create pending invite (expires in 7 days)

**Role Change Constraints:**

- ADMIN cannot change OWNER role
- ADMIN cannot remove OWNER
- OWNER can make another member OWNER (confirmation dialog)
- User being changed receives notification

-----

## **3.3 Provider Credentials**

### **FR-PC-001: Add Provider Credential**

**Priority:** P0 (Must Have)  
**User Story:** As a project admin, I want to add API credentials for LLM providers so experiments can run.

**Acceptance Criteria:**

- User selects provider from dropdown
- User enters API key (masked input)
- User gives credential a label (e.g., “OpenAI - Production”)
- API key is validated before saving (test call)
- API key is encrypted at rest (libsodium sealed box)
- Multiple credentials per provider allowed

**Supported Providers (v1):**

|Provider         |Config Fields                                       |Test Endpoint                                                                                 |
|-----------------|----------------------------------------------------|----------------------------------------------------------------------------------------------|
|**OpenAI**       |• API Key<br>• Organization ID (optional)           |`GET /v1/models`                                                                              |
|**Anthropic**    |• API Key                                           |`POST /v1/messages` (with test prompt)                                                        |
|**Google Vertex**|• Project ID<br>• Location<br>• Service Account JSON|`POST /v1/projects/{project}/locations/{location}/publishers/google/models/gemini-pro:predict`|
|**AWS Bedrock**  |• Access Key ID<br>• Secret Access Key<br>• Region  |`POST /model/{modelId}/invoke`                                                                |
|**Azure OpenAI** |• Endpoint URL<br>• API Key<br>• Deployment Name    |`GET /openai/deployments`                                                                     |
|**Ollama**       |• Base URL (http://localhost:11434)                 |`GET /api/tags`                                                                               |

**Validation Logic:**

```typescript
async function validateOpenAICredential(apiKey: string): Promise<boolean> {
  try {
    const response = await fetch('https://api.openai.com/v1/models', {
      headers: { 'Authorization': `Bearer ${apiKey}` },
    });
    return response.ok;
  } catch (error) {
    return false;
  }
}
```

**Encryption:**

```typescript
import sodium from 'libsodium-wrappers';

async function encryptApiKey(apiKey: string): Promise<string> {
  await sodium.ready;
  const publicKey = Buffer.from(process.env.ENCRYPTION_PUBLIC_KEY!, 'hex');
  const encrypted = sodium.crypto_box_seal(
    Buffer.from(apiKey, 'utf8'),
    publicKey
  );
  return Buffer.from(encrypted).toString('base64');
}

async function decryptApiKey(encrypted: string): Promise<string> {
  await sodium.ready;
  const publicKey = Buffer.from(process.env.ENCRYPTION_PUBLIC_KEY!, 'hex');
  const privateKey = Buffer.from(process.env.ENCRYPTION_PRIVATE_KEY!, 'hex');
  const decrypted = sodium.crypto_box_seal_open(
    Buffer.from(encrypted, 'base64'),
    publicKey,
    privateKey
  );
  return Buffer.from(decrypted).toString('utf8');
}
```

**Error Cases:**

- `INVALID_KEY`: Test call fails → Show “Invalid API key”
- `NETWORK_ERROR`: Cannot reach provider → Show “Cannot connect to provider”
- `QUOTA_EXCEEDED`: API quota exceeded → Show “API quota exceeded”
- `DUPLICATE_LABEL`: Label already exists → Show “Label already in use”

### **FR-PC-002: Manage Credentials**

**Priority:** P0 (Must Have)

**Actions:**

- **List**: Show all credentials with masked keys (last 4 chars visible)
- **Edit**: Change label only (cannot edit API key; must delete and recreate)
- **Delete**: Remove credential (confirmation dialog)
- **Test**: Re-run validation test
- **Set Default**: Mark one credential per provider as default

**Constraints:**

- Cannot delete credential if used in active experiments
- Must have at least one active credential to run experiments

-----

## **3.4 Experiment Creation (Wizard)**

### **FR-EC-001: Wizard - Step 1: Objective**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to define what I’m trying to achieve so the system can help me build a good prompt.

**UI Layout:**

```
┌────────────────────────────────────────────────────────┐
│  Step 1 of 7: Define Objective                         │
├────────────────────────────────────────────────────────┤
│                                                         │
│  What are you trying to achieve with this prompt?      │
│  Be specific about the task, audience, and desired     │
│  output quality.                                        │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │ [Empty multiline textarea, 4 rows min]          │  │
│  │                                                  │  │
│  │ Placeholder:                                     │  │
│  │ "Example: Generate helpful, empathetic customer │  │
│  │  support responses that resolve issues quickly  │  │
│  │  while maintaining brand voice..."               │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  Character count: 0 / 2000                             │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │          AI Assist Panel                         │  │
│  │  ✨ Let AI help you:                             │  │
│  │                                                  │  │
│  │  [Draft 3 Options] [Improve] [Add Details]      │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  OR choose a template:                                 │
│  [Customer Support] [Creative Writing]                 │
│  [Data Extraction] [Code Generation]                   │
│                                                         │
│  [← Back]                        [Continue →]          │
└────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

- Textarea supports markdown (preview toggle)
- Min length: 20 characters
- Max length: 2,000 characters
- AI Assist “Draft” generates 3 objective options
- Templates pre-fill objective + rubric + sample prompt
- “Continue” button disabled until valid input
- Auto-saves draft every 30 seconds

**Validation:**

```typescript
const objectiveSchema = z.object({
  goal: z.string()
    .min(20, 'Objective must be at least 20 characters')
    .max(2000, 'Objective too long'),
});
```

**AI Assist - Draft Objectives:**

**System Prompt:**

```
You are a prompt engineering expert. The user will provide vague hints about what they want to achieve. Your job is to expand this into 3 clear, specific objective statements.

Each objective should:
- Be 1-2 paragraphs
- Define the task clearly
- Specify the target audience
- Describe desired output characteristics
- Include success criteria

Return JSON:
{
  "options": [
    {"title": "Option 1", "text": "..."},
    {"title": "Option 2", "text": "..."},
    {"title": "Option 3", "text": "..."}
  ]
}
```

**User Prompt Template:**

```
User hints: {{userInput}}

Generate 3 objective options with different focuses:
1. Clarity-focused (precise, unambiguous)
2. Creativity-focused (flexible, open-ended)
3. Efficiency-focused (concise, fast)
```

**Templates:**

```typescript
const templates = {
  'customer-support': {
    name: 'Customer Support Bot',
    objective: `Generate helpful, empathetic responses to customer inquiries that:
- Resolve issues quickly and accurately
- Maintain a friendly, professional tone
- Follow company policies and guidelines
- Escalate complex issues appropriately
- Build customer trust and satisfaction`,
    rubric: [
      { name: 'Helpfulness', description: 'Provides actionable solution', weight: 0.35, scale: { min: 0, max: 5 } },
      { name: 'Empathy', description: 'Acknowledges customer emotions', weight: 0.25, scale: { min: 0, max: 5 } },
      { name: 'Accuracy', description: 'Factually correct information', weight: 0.25, scale: { min: 0, max: 5 } },
      { name: 'Conciseness', description: 'Clear and brief', weight: 0.15, scale: { min: 0, max: 5 } },
    ],
    seedPrompt: `You are a customer support agent for [Company Name]...`,
    sampleCases: [...],
  },
  // ... more templates
};
```

### **FR-EC-002: Wizard - Step 2: Rubric**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to define evaluation criteria so I can measure prompt quality objectively.

**UI Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Step 2 of 7: Define Evaluation Rubric                   │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  A rubric defines the criteria judges will use to        │
│  evaluate prompt outputs. Each criterion has a weight    │
│  (importance) and a scale.                               │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          AI Assist Panel                            │ │
│  │  [Draft Rubric from Objective]                      │ │
│  │  [Add Criterion] [Normalize Weights]                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────┬─────────────────┬────────┬──────────────┐ │
│  │ Criterion│ Description     │ Weight │ Scale        │ │
│  ├─────────┼─────────────────┼────────┼──────────────┤ │
│  │ [Input] │ [Textarea 2 row]│ [0.35] │ [0-5 ▼]      │ │
│  │ Helpful-│ Provides actio- │  0.35  │ 0-5 (6 pts)  │ │
│  │ ness    │ nable solution  │        │ [Edit] [Del] │ │
│  ├─────────┼─────────────────┼────────┼──────────────┤ │
│  │ Empathy │ Acknowledges    │  0.25  │ 0-5          │ │
│  │         │ emotions        │        │              │ │
│  ├─────────┼─────────────────┼────────┼──────────────┤ │
│  │ Accuracy│ Factually       │  0.25  │ 0-5          │ │
│  │         │ correct         │        │              │ │
│  ├─────────┼─────────────────┼────────┼──────────────┤ │
│  │ Concise │ Clear and brief │  0.15  │ 0-5          │ │
│  └─────────┴─────────────────┴────────┴──────────────┘ │
│                                                           │
│  Total Weight: 1.00 ✓                                    │
│                                                           │
│  [+ Add Criterion]                                        │
│                                                           │
│  [← Back]                          [Continue →]          │
└──────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

- Minimum 2 criteria, maximum 10 criteria
- Each criterion has:
  - Name: 1-50 chars, alphanumeric + spaces
  - Description: 10-500 chars
  - Weight: 0.0-1.0 (decimals allowed)
  - Scale: dropdown (0-1, 0-3, 0-5, 0-10, 0-100)
- Weights must sum to 1.0 (±0.01 tolerance)
- “Normalize Weights” button distributes weights evenly
- Drag-to-reorder criteria
- Real-time weight sum validation

**Validation:**

```typescript
const criterionSchema = z.object({
  name: z.string().min(1).max(50).regex(/^[a-zA-Z0-9\s]+$/),
  description: z.string().min(10).max(500),
  weight: z.number().min(0).max(1),
  scale: z.object({
    min: z.number(),
    max: z.number(),
    labels: z.record(z.string()).optional(),
  }),
});

const rubricSchema = z.array(criterionSchema)
  .min(2, 'At least 2 criteria required')
  .max(10, 'Maximum 10 criteria')
  .refine((criteria) => {
    const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0);
    return Math.abs(totalWeight - 1.0) < 0.01;
  }, { message: 'Weights must sum to 1.0' });
```

**AI Assist - Draft Rubric:**

**System Prompt:**

```
You are a prompt evaluation expert. Based on the user's objective, propose a balanced rubric with 4-6 criteria.

Guidelines:
- Cover all important aspects of the objective
- Balance high-level goals (helpfulness) with specific requirements (accuracy)
- Suggest reasonable weights (no criterion > 40%)
- Use 0-5 scale for all criteria

Return JSON:
{
  "criteria": [
    {
      "name": "Criterion Name",
      "description": "Clear description of what to evaluate",
      "weight": 0.25,
      "scale": {"min": 0, "max": 5}
    }
  ]
}
```

**User Prompt Template:**

```
Objective:
{{objective}}

Generate a rubric with 4-6 evaluation criteria. Weights must sum to 1.0.
```

**Normalize Weights Logic:**

```typescript
function normalizeWeights(criteria: Criterion[]): Criterion[] {
  const equalWeight = 1.0 / criteria.length;
  return criteria.map(c => ({ ...c, weight: equalWeight }));
}
```

### **FR-EC-003: Wizard - Step 3: Seed Prompt**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to create an initial prompt that will be iteratively refined.

**UI Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Step 3 of 7: Create Seed Prompt                         │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Write your initial prompt. This will be tested and      │
│  refined iteratively.                                     │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          AI Assist Panel                            │ │
│  │  [Draft 3 Prompts] [Improve] [Add Constraints]      │ │
│  │  [Test with Example]                                 │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │  [System Message] [Main Prompt] [Few-Shot Examples]│ │
│  │  ─────────────────────────────────────────────────  │ │
│  │                                                     │ │
│  │  [Monaco Editor - 20 rows]                         │ │
│  │                                                     │ │
│  │  You are a helpful assistant...                    │ │
│  │                                                     │ │
│  │  When the user asks {{question}}, respond with     │ │
│  │  a clear, concise answer that {{requirements}}.   │ │
│  │                                                     │ │
│  │  [Syntax highlighting, variable detection]         │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  Variables detected: {{question}}, {{requirements}}      │
│                                                           │
│  [Advanced Options ▼]                                    │
│    • System Message (optional)                           │
│    • Few-Shot Examples (optional)                        │
│    • Function/Tool Definitions (optional)                │
│                                                           │
│  [← Back]                          [Continue →]          │
└──────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

- Monaco editor with syntax highlighting
- Detects template variables in `{{variable}}` format
- Min length: 50 characters
- Max length: 20,000 characters
- Optional system message (separate textarea)
- Optional few-shot examples (add/remove dynamically)
- Optional tool definitions (JSON editor)
- “Test with Example” opens preview pane
- Real-time character/token count

**Validation:**

```typescript
const promptSchema = z.object({
  text: z.string().min(50).max(20000),
  systemText: z.string().max(5000).optional(),
  fewShots: z.array(z.object({
    user: z.string(),
    assistant: z.string(),
  })).max(10).optional(),
  toolsSchema: z.any().optional(), // Validated as JSON schema
});
```

**Variable Detection:**

```typescript
function detectVariables(prompt: string): string[] {
  const regex = /\{\{(\w+)\}\}/g;
  const variables = new Set<string>();
  let match;
  while ((match = regex.exec(prompt)) !== null) {
    variables.add(match[1]);
  }
  return Array.from(variables);
}
```

**AI Assist - Draft Prompts:**

**System Prompt:**

```
You are an expert prompt engineer. Based on the objective and rubric, generate 3 different prompt approaches:

1. **Structured**: Clear sections, explicit instructions, numbered steps
2. **Conversational**: Natural language, examples, friendly tone
3. **Minimal**: Concise, focused, essential instructions only

Each prompt should:
- Address the objective directly
- Include constraints from the rubric
- Use template variables ({{variable}}) for dynamic inputs
- Be production-ready (no placeholders)

Return JSON:
{
  "prompts": [
    {
      "name": "Structured Approach",
      "text": "...",
      "systemText": "...",
      "rationale": "Why this approach might work"
    }
  ]
}
```

**User Prompt Template:**

```
Objective:
{{objective}}

Rubric:
{{rubric_json}}

Generate 3 different prompt approaches. Include template variables where user input is needed.
```

### **FR-EC-004: Wizard - Step 4: Test Data**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to define test cases to evaluate my prompt against.

**UI Layout:**

```
┌────────────────────────────────────────────────────────────┐
│  Step 4 of 7: Prepare Test Data                            │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Add test cases to evaluate your prompt. You can:          │
│  • Upload a CSV/JSONL file                                 │
│  • Generate synthetic cases with AI                        │
│  • Add cases manually                                      │
│                                                             │
│  [Golden] [Synthetic] [Adversarial]                        │
│  ──────────────────────────────────────────────────────    │
│                                                             │
│  📁 Upload File                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Drag & drop CSV or JSONL file here                  │ │
│  │  or [Browse Files]                                    │ │
│  │                                                        │ │
│  │  Supported formats:                                   │ │
│  │  • CSV with headers                                   │ │
│  │  • JSONL (one JSON object per line)                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ✨ Generate with AI                                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Domain hints: [customer support inquiries]          │ │
│  │  Count: [50] cases                                    │ │
│  │  Diversity: [────●──] 7/10                            │ │
│  │  [Generate Synthetic Cases]                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ➕ Add Manually                                           │
│  [+ Add Test Case]                                         │
│                                                             │
│  Current dataset: 0 cases                                  │
│                                                             │
│  [← Back]                            [Continue →]          │
└────────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

**Upload File:**

- Accepts CSV (with headers) and JSONL
- File size limit: 10 MB
- Max rows: 1,000
- Shows upload progress
- Preview first 10 rows before import
- Map columns to variables (detected from prompt)
- Validate all rows before import
- Option to tag all imported cases

**Generate Synthetic:**

- User provides domain hints (textarea)
- Slider for count (10-500 cases)
- Slider for diversity (1-10, higher = more varied)
- Optional: specify languages, length buckets
- Shows estimated cost before generation
- Progress bar during generation
- Preview generated cases before adding

**Manual Entry:**

- Form with fields for each prompt variable
- Optional: expected output, tags, difficulty
- Save as you go (draft state)

**Validation:**

```typescript
const datasetUploadSchema = z.object({
  file: z.instanceof(File)
    .refine((f) => f.size <= 10 * 1024 * 1024, 'File too large (max 10MB)')
    .refine((f) => ['text/csv', 'application/jsonl'].includes(f.type), 'Invalid format'),
});

const syntheticGenSchema = z.object({
  domainHints: z.string().min(20).max(1000),
  count: z.number().int().min(10).max(500),
  diversity: z.number().min(1).max(10),
  languages: z.array(z.string()).optional(),
  lengthBuckets: z.array(z.enum(['XS', 'S', 'M', 'L', 'XL'])).optional(),
});
```

**CSV Mapping Flow:**

1. Parse CSV headers
1. Show column mapping interface:
   
   ```
   CSV Column          →    Prompt Variable
   [question ▼]        →    {{question}}
   [context ▼]         →    {{context}}
   [expected_answer ▼] →    (expected output)
   [category ▼]        →    (tag)
   ```
1. Validate mappings (all required variables covered)
1. Preview mapped data
1. Import

**JSONL Format:**

```json
{"input": {"question": "...", "context": "..."}, "expected": "...", "tags": ["tag1"]}
{"input": {"question": "...", "context": "..."}, "expected": "...", "tags": ["tag2"]}
```

**AI Assist - Generate Synthetic:**

**System Prompt:**

```
You are a test data generator. Based on the domain and requirements, generate realistic, diverse test cases.

Requirements:
- Vary complexity (simple, moderate, complex)
- Include edge cases (empty inputs, very long inputs, ambiguous phrasing)
- Vary entities and contexts
- Match the specified diversity level
- Generate exactly the requested count

Return JSONL format:
{"input": {...}, "tags": [...], "difficulty": 1-5}
```

**User Prompt Template:**

```
Domain: {{domain_hints}}
Prompt variables: {{variable_names}}
Count: {{count}}
Diversity: {{diversity}}/10

Generate {{count}} diverse test cases. Each case should have an "input" object with values for all variables, plus "tags" and "difficulty".
```

**Coverage Heatmap (Advanced):**

```
┌────────────────────────────────────────────┐
│  Coverage Analysis                          │
├────────────────────────────────────────────┤
│                                             │
│  Tags:           ████░░░░  45% coverage    │
│  Entities:       ██████░░  60% coverage    │
│  Length (XS-XL): ███████░  75% coverage    │
│  Ambiguity:      ████░░░░  40% coverage    │
│  Languages:      ██░░░░░░  20% coverage    │
│                                             │
│  [Fill Coverage Gaps with AI]              │
└────────────────────────────────────────────┘
```

### **FR-EC-005: Wizard - Step 5: Models & Parameters**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to select which models to test my prompt against.

**UI Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Step 5 of 7: Configure Models                           │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Select which models to test your prompt against.        │
│  Different models may perform differently.               │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          AI Assist Panel                            │ │
│  │  [Recommend Balanced Set] [Prune Costly Models]     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  Provider: [All ▼] [OpenAI] [Anthropic] [Google]        │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐│
│  │ ☑ OpenAI GPT-4o                          $0.0050/1K ││
│  │   Temperature: [1.0] Max Tokens: [4096]             ││
│  │   [⚙️ Advanced Parameters]                           ││
│  ├─────────────────────────────────────────────────────┤│
│  │ ☑ OpenAI GPT-4o-mini                     $0.0003/1K ││
│  │   Temperature: [1.0] Max Tokens: [4096]             ││
│  ├─────────────────────────────────────────────────────┤│
│  │ ☑ Anthropic Claude Sonnet 4             $0.0030/1K ││
│  │   Temperature: [1.0] Max Tokens: [4096]             ││
│  ├─────────────────────────────────────────────────────┤│
│  │ ☐ Anthropic Claude Opus 4.1              $0.0150/1K ││
│  │   (Expensive - use sparingly)                       ││
│  ├─────────────────────────────────────────────────────┤│
│  │ ☐ Google Gemini 1.5 Pro                 $0.0035/1K ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Selected: 3 models × 50 cases = 150 runs               │
│  Estimated cost: $2.10 - $3.50                          │
│                                                           │
│  Parameter Grid (Advanced):                              │
│  [+ Add Temperature Variation]                           │
│  [+ Add Max Tokens Variation]                            │
│                                                           │
│  [← Back]                            [Continue →]        │
└──────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

- List all models from active provider credentials
- Show pricing per 1K tokens (input + output averaged)
- Allow selecting multiple models
- Each model has collapsible parameter config:
  - Temperature: 0.0-2.0, step 0.1, default 1.0
  - Max Tokens: 1-100000, default 4096
  - Top P: 0.0-1.0, step 0.05, default 1.0 (advanced)
  - Frequency Penalty: -2.0 to 2.0, step 0.1, default 0 (advanced)
  - Presence Penalty: -2.0 to 2.0, step 0.1, default 0 (advanced)
  - Seed: integer, optional (for reproducibility)
- Show estimated cost based on selections
- “Recommend Balanced Set” suggests 2-3 models (fast/balanced/smart)
- “Prune Costly” removes models with cost > $0.01/1K

**Parameter Grid:**

- Advanced feature to test multiple parameter combinations
- Example: Temperature [0.7, 1.0, 1.3] × Max Tokens [2048, 4096]
- Each combination counts as separate model run
- Shows: N models × M param combos × K cases = Total runs

**Validation:**

```typescript
const modelConfigSchema = z.object({
  provider: z.enum(['OPENAI', 'ANTHROPIC', 'GOOGLE_VERTEX', 'AWS_BEDROCK', 'AZURE_OPENAI', 'OLLAMA']),
  modelId: z.string(),
  params: z.object({
    temperature: z.number().min(0).max(2).default(1.0),
    maxTokens: z.number().int().min(1).max(100000).optional(),
    topP: z.number().min(0).max(1).optional(),
    frequencyPenalty: z.number().min(-2).max(2).optional(),
    presencePenalty: z.number().min(-2).max(2).optional(),
    stop: z.array(z.string()).max(4).optional(),
  }),
  seed: z.number().int().optional(),
});

const modelSelectionSchema = z.array(modelConfigSchema)
  .min(1, 'Select at least one model')
  .max(10, 'Maximum 10 model configurations');
```

**Cost Estimation Logic:**

```typescript
function estimateCost(
  models: ModelConfig[],
  caseCount: number,
  avgPromptTokens: number, // Estimated from prompt + avg case
  avgCompletionTokens: number // Estimated (default: 500)
): { min: number; max: number } {
  let minCost = 0;
  let maxCost = 0;
  
  for (const model of models) {
    const pricing = getPricing(model.provider, model.modelId);
    const costPerCase = (
      (avgPromptTokens * pricing.input / 1000) +
      (avgCompletionTokens * pricing.output / 1000)
    );
    
    minCost += costPerCase * caseCount * 0.8; // -20% variance
    maxCost += costPerCase * caseCount * 1.2; // +20% variance
  }
  
  return { min: minCost, max: maxCost };
}
```

### **FR-EC-006: Wizard - Step 6: Judges & Safety**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to configure how my prompt outputs will be evaluated.

**UI Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Step 6 of 7: Configure Judges & Safety                  │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Judges evaluate prompt outputs against your rubric.     │
│  Multiple judges provide more reliable scores.           │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          AI Assist Panel                            │ │
│  │  [Recommend Judge Set] [Test Judge Prompts]         │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  Pointwise Judges (score each output individually)      │
│  ┌─────────────────────────────────────────────────────┐│
│  │ ☑ GPT-4o (Fast, reliable)               $0.0050/1K ││
│  │ ☑ Claude Sonnet 4 (Strict, detailed)    $0.0030/1K ││
│  │ ☑ GPT-4o-mini (Budget option)           $0.0003/1K ││
│  │ ☐ GPT-4-turbo (Slower, thorough)        $0.0100/1K ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Pairwise Judges (compare outputs side-by-side)         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ ☑ Enable pairwise comparison                        ││
│  │ Judge: [Claude Sonnet 4 ▼]                          ││
│  │ Randomize order: ☑ (prevents position bias)         ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Safety Checks                                           │
│  ┌─────────────────────────────────────────────────────┐│
│  │ ☑ Content moderation (OpenAI API)                   ││
│  │ ☑ PII detection (regex + NER)                       ││
│  │ ☑ Jailbreak detection (pattern matching)            ││
│  │ ☑ Toxicity check (Perspective API)                  ││
│  │                                                      ││
│  │ Block outputs with violations: ☑                    ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Selected: 3 pointwise + 1 pairwise = 4 judges          │
│  Estimated judging cost: $1.20 per iteration            │
│                                                           │
│  [← Back]                            [Continue →]        │
└──────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

**Pointwise Judges:**

- Minimum 1 judge, maximum 5 judges
- Each judge uses same rubric
- Judges can be same or different models
- Each judge gets identical prompt template
- Temperature fixed at 0.3 for consistency
- Seed fixed at 42 for reproducibility

**Pairwise Judges:**

- Optional (can disable)
- Only one pairwise judge (comparing all outputs)
- Identity-blind (hide which model generated which output)
- Randomized order (A vs B, then B vs A)
- Results in win/loss/tie matrix

**Safety Checks:**

- Content Moderation: OpenAI moderation API
- PII Detection: Regex for SSN, credit cards, emails, phone numbers
- Jailbreak: Pattern matching for known attack vectors
- Toxicity: Optional Perspective API integration
- Configurable: block outputs vs. flag for review

**Validation:**

```typescript
const judgeConfigSchema = z.object({
  pointwiseJudges: z.array(z.object({
    provider: z.enum(['OPENAI', 'ANTHROPIC', 'GOOGLE_VERTEX']),
    modelId: z.string(),
  })).min(1).max(5),
  pairwiseEnabled: z.boolean(),
  pairwiseJudge: z.object({
    provider: z.enum(['OPENAI', 'ANTHROPIC', 'GOOGLE_VERTEX']),
    modelId: z.string(),
  }).optional(),
  safetyChecks: z.object({
    contentModeration: z.boolean(),
    piiDetection: z.boolean(),
    jailbreakDetection: z.boolean(),
    toxicityCheck: z.boolean(),
    blockViolations: z.boolean(),
  }),
});
```

**Judge Prompt Template (Pointwise):**

```
# Evaluation Task

You are a strict evaluator. Score the output against the rubric below.

## Goal
{{experiment_goal}}

## Rubric
{{rubric_json}}

## Input
{{case_input_json}}

## Output to Evaluate
{{model_output}}

## Instructions
Evaluate the output against each criterion. Return ONLY valid JSON:

{
  "scores": {
    "Criterion1": 4,
    "Criterion2": 5
  },
  "rationales": {
    "Criterion1": "Brief 1-2 sentence explanation",
    "Criterion2": "Brief 1-2 sentence explanation"
  },
  "safetyFlags": {
    "policyViolation": false,
    "piiDetected": false,
    "toxicContent": false,
    "jailbreakAttempt": false
  }
}

Be strict and objective. No chain-of-thought, just scores and rationales.
```

**Pairwise Judge Prompt Template:**

```
# Pairwise Comparison

Compare two outputs for the same input. Which one better achieves the goal?

## Goal
{{experiment_goal}}

## Rubric
{{rubric_json}}

## Input
{{case_input_json}}

## Output A
{{output_a}}

## Output B
{{output_b}}

## Instructions
Determine which output is better overall. Return ONLY valid JSON:

{
  "winner": "A" | "B" | "tie",
  "reasons": ["Reason 1", "Reason 2"],
  "scores": {
    "A": {"Criterion1": 4, "Criterion2": 5},
    "B": {"Criterion1": 3, "Criterion2": 5}
  }
}

Be objective. Consider all rubric criteria.
```

**Safety Check Implementations:**

```typescript
// PII Detection
const PII_PATTERNS = {
  ssn: /\b\d{3}-\d{2}-\d{4}\b/g,
  creditCard: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g,
  email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
  phone: /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g,
};

function detectPII(text: string): string[] {
  const violations: string[] = [];
  for (const [type, pattern] of Object.entries(PII_PATTERNS)) {
    if (pattern.test(text)) {
      violations.push(type);
    }
  }
  return violations;
}

// Jailbreak Detection
const JAILBREAK_PATTERNS = [
  /ignore previous instructions/i,
  /disregard all prior/i,
  /you are now in DAN mode/i,
  /pretend you are/i,
  // ... more patterns
];

function detectJailbreak(text: string): boolean {
  return JAILBREAK_PATTERNS.some(pattern => pattern.test(text));
}
```

### **FR-EC-007: Wizard - Step 7: Stop Rules & Budget**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to set limits on the optimization process to control cost and time.

**UI Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Step 7 of 7: Stop Rules & Budget                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Control when the optimization loop stops to prevent     │
│  runaway costs and infinite iterations.                  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │          AI Assist Panel                            │ │
│  │  [Estimate Total Cost] [Suggest Reasonable Limits]  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  Maximum Iterations                                      │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Stop after: [10] iterations                         ││
│  │ (Recommended: 5-15)                                  ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Convergence Threshold                                   │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Stop if improvement < [0.02] (2%)                   ││
│  │ for [3] consecutive iterations                       ││
│  │ (Recommended: 1-3% over 2-3 iterations)             ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Budget Limits                                           │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Maximum spend: $[100.00]                            ││
│  │ Alert at: [80]% of budget                           ││
│  │                                                      ││
│  │ Maximum tokens: [1,000,000] (optional)              ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Early Stopping (Advanced)                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │ ☑ Prune low-performing prompts after iteration 2    ││
│  │ ☑ Stop if no refinement suggestions generated       ││
│  │ ☐ Adaptive sampling (fewer cases for weak prompts)  ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Estimated Total Cost: $15-25 (for full 10 iterations)  │
│  ⚠️ Actual cost may vary based on output lengths        │
│                                                           │
│  [← Back]                   [Create Experiment →]        │
└──────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

- Max iterations: 1-100, default 10
- Min delta threshold: 0-1.0, default 0.02 (2%)
- Convergence window: 1-10 iterations, default 3
- Max budget: $0-10,000, default $100
- Budget alert threshold: 50-100%, default 80%
- Max tokens: optional, 0-10,000,000
- Early stopping options (checkboxes)
- Cost estimator shows range based on:
  - Selected models × parameter combos
  - Test case count
  - Judges × iterations
  - Average tokens per case (estimated)

**Validation:**

```typescript
const stopRulesSchema = z.object({
  maxIterations: z.number().int().min(1).max(100).default(10),
  minDeltaThreshold: z.number().min(0).max(1).default(0.02),
  convergenceWindow: z.number().int().min(1).max(10).default(3),
  maxBudgetUsd: z.number().min(0).max(10000).default(100),
  budgetAlertThreshold: z.number().min(0.5).max(1).default(0.8),
  maxTotalTokens: z.number().int().min(0).optional(),
  earlyStoppingConfig: z.object({
    pruneWeakPrompts: z.boolean().default(true),
    stopIfNoRefinement: z.boolean().default(true),
    adaptiveSampling: z.boolean().default(false),
  }),
});
```

**Cost Estimation Logic:**

```typescript
function estimateTotalCost(experimentConfig: ExperimentConfig): { min: number; max: number } {
  const {
    models,
    judges,
    caseCount,
    maxIterations,
    avgPromptTokens,
    avgCompletionTokens,
  } = experimentConfig;
  
  // Execution cost per iteration
  const execCostPerIteration = models.reduce((sum, model) => {
    const pricing = getPricing(model.provider, model.modelId);
    return sum + (
      (avgPromptTokens * pricing.input / 1000) +
      (avgCompletionTokens * pricing.output / 1000)
    ) * caseCount;
  }, 0);
  
  // Judging cost per iteration
  const judgeCostPerIteration = judges.pointwise.reduce((sum, judge) => {
    const pricing = getPricing(judge.provider, judge.modelId);
    const judgePromptTokens = 500; // Estimated
    const judgeCompletionTokens = 200; // Estimated
    return sum + (
      (judgePromptTokens * pricing.input / 1000) +
      (judgeCompletionTokens * pricing.output / 1000)
    ) * caseCount * models.length; // Judge each model's output
  }, 0);
  
  // Refinement cost per iteration
  const refineCostPerIteration = 0.50; // Estimated $0.50/refinement
  
  // Total per iteration
  const costPerIteration = execCostPerIteration + judgeCostPerIteration + refineCostPerIteration;
  
  // With early stopping, assume 60-80% of max iterations
  const minIterations = Math.ceil(maxIterations * 0.6);
  const maxCost = costPerIteration * maxIterations;
  const minCost = costPerIteration * minIterations;
  
  return { min: minCost, max: maxCost };
}
```

**Final Confirmation:**
After clicking “Create Experiment”, show confirmation dialog:

```
┌────────────────────────────────────────┐
│  Create Experiment?                     │
├────────────────────────────────────────┤
│                                         │
│  You're about to create:                │
│  • 3 model configurations               │
│  • 50 test cases                        │
│  • 3 judges                             │
│  • Up to 10 iterations                  │
│                                         │
│  Estimated cost: $15-25                 │
│  Estimated time: 20-30 minutes          │
│                                         │
│  [Cancel]              [Create & Run →] │
└────────────────────────────────────────┘
```

-----

## **3.5 Experiment Execution**

### **FR-EE-001: Start Iteration**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to start testing my prompt so I can see how well it performs.

**Acceptance Criteria:**

- “Run Iteration” button on experiment dashboard
- Confirmation dialog shows estimated cost & time
- Creates new Iteration record with status PENDING
- Validates:
  - At least one prompt version exists
  - At least one model config active
  - At least one judge config active
  - At least one test case in datasets
  - Provider credentials valid
  - Budget not exceeded
- Enqueues execution jobs to BullMQ
- Redirects to live iteration view
- Real-time progress via Server-Sent Events

**Pre-Run Validation:**

```typescript
async function validateExperimentReady(experimentId: string): Promise<ValidationResult> {
  const errors: string[] = [];
  
  const experiment = await prisma.experiment.findUnique({
    where: { id: experimentId },
    include: {
      promptVersions: true,
      modelConfigs: { where: { isActive: true } },
      judgeConfigs: { where: { isActive: true } },
      project: {
        include: {
          datasets: { include: { cases: true } },
          providers: { where: { isActive: true } },
        },
      },
    },
  });
  
  if (!experiment) {
    errors.push('Experiment not found');
    return { valid: false, errors };
  }
  
  if (experiment.promptVersions.length === 0) {
    errors.push('No prompt version found. Create a prompt first.');
  }
  
  if (experiment.modelConfigs.length === 0) {
    errors.push('No active model configs. Add at least one model.');
  }
  
  if (experiment.judgeConfigs.length === 0) {
    errors.push('No active judge configs. Add at least one judge.');
  }
  
  const totalCases = experiment.project.datasets.reduce(
    (sum, ds) => sum + ds.cases.length,
    0
  );
  
  if (totalCases === 0) {
    errors.push('No test cases found. Upload or generate test data.');
  }
  
  // Check budget
  const totalSpend = await getTotalSpend(experiment.projectId);
  const stopRules = experiment.stopRules as StopRules;
  
  if (stopRules.maxBudgetUsd && totalSpend >= stopRules.maxBudgetUsd) {
    errors.push(`Budget exceeded: $${totalSpend} / $${stopRules.maxBudgetUsd}`);
  }
  
  return { valid: errors.length === 0, errors };
}
```

**Job Orchestration:**

```typescript
async function startIteration(experimentId: string, promptVersionId: string): Promise<string> {
  // Validate
  const validation = await validateExperimentReady(experimentId);
  if (!validation.valid) {
    throw new Error(validation.errors.join('; '));
  }
  
  // Create iteration
  const iteration = await prisma.iteration.create({
    data: {
      experimentId,
      promptVersionId,
      number: await getNextIterationNumber(experimentId),
      status: 'PENDING',
    },
  });
  
  // Get configs
  const experiment = await prisma.experiment.findUniqueOrThrow({
    where: { id: experimentId },
    include: {
      modelConfigs: { where: { isActive: true } },
      project: {
        include: {
          datasets: { include: { cases: true } },
        },
      },
    },
  });
  
  // Create model runs
  const modelRuns = await Promise.all(
    experiment.modelConfigs.map((config) =>
      prisma.modelRun.create({
        data: {
          iterationId: iteration.id,
          promptVersionId,
          modelConfigId: config.id,
          datasetId: experiment.project.datasets[0].id, // Use first dataset
          status: 'PENDING',
        },
      })
    )
  );
  
  // Enqueue execution jobs
  await Promise.all(
    modelRuns.map((run) =>
      executeQueue.add('execute-run', {
        modelRunId: run.id,
        iterationId: iteration.id,
      }, {
        priority: 1,
        attempts: 3,
        backoff: { type: 'exponential', delay: 2000 },
      })
    )
  );
  
  // Update status
  await prisma.iteration.update({
    where: { id: iteration.id },
    data: { status: 'EXECUTING', startedAt: new Date() },
  });
  
  // Publish SSE event
  await redis.publish('iterations', JSON.stringify({
    type: 'iteration:started',
    iterationId: iteration.id,
  }));
  
  return iteration.id;
}
```

### **FR-EE-002: Real-Time Progress Updates**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to see real-time progress of my experiment so I know what’s happening.

**UI Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Iteration #3 - Running                        ⏸ Pause   │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────────┐│
│  │  1. Dataset Loading          ✓ Complete (2s)       ││
│  ├─────────────────────────────────────────────────────┤│
│  │  2. Executing Runs           ⏳ In Progress (45%)   ││
│  │     • GPT-4o: 25/50 cases    [████████░░░░] 50%    ││
│  │     • Claude Sonnet: 20/50   [███████░░░░░] 40%    ││
│  │     • GPT-4o-mini: 22/50     [████████░░░░] 44%    ││
│  ├─────────────────────────────────────────────────────┤│
│  │  3. Judging Outputs          ⏸ Waiting             ││
│  ├─────────────────────────────────────────────────────┤│
│  │  4. Aggregating Scores       ⏸ Waiting             ││
│  ├─────────────────────────────────────────────────────┤│
│  │  5. Refining Prompt          ⏸ Waiting             ││
│  ├─────────────────────────────────────────────────────┤│
│  │  6. Human Review             ⏸ Waiting             ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Cost so far: $1.23 / $100 budget (1.2%)                │
│  Tokens used: 45,230 / 1,000,000 (4.5%)                 │
│  Elapsed time: 2m 34s                                    │
│  Estimated completion: ~3 minutes                        │
│                                                           │
│  [View Live Outputs →]                                   │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**SSE Implementation:**

```typescript
// API route: /api/iterations/[id]/stream
export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const iterationId = params.id;
  
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      
      // Subscribe to Redis pub/sub
      const subscriber = redis.duplicate();
      await subscriber.subscribe(`iteration:${iterationId}`);
      
      subscriber.on('message', (channel, message) => {
        const data = JSON.parse(message);
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      });
      
      // Send heartbeat every 15s
      const heartbeat = setInterval(() => {
        controller.enqueue(encoder.encode(': heartbeat\n\n'));
      }, 15000);
      
      // Cleanup on close
      request.signal.addEventListener('abort', () => {
        clearInterval(heartbeat);
        subscriber.unsubscribe();
        subscriber.quit();
        controller.close();
      });
    },
  });
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

**Event Types:**

```typescript
type IterationEvent =
  | { type: 'iteration:started'; iterationId: string }
  | { type: 'status:changed'; status: IterationStatus }
  | { type: 'run:progress'; modelRunId: string; completed: number; total: number }
  | { type: 'run:completed'; modelRunId: string; cost: number; tokens: number }
  | { type: 'judge:progress'; completed: number; total: number }
  | { type: 'aggregate:completed'; metrics: any }
  | { type: 'refine:completed'; suggestionId: string }
  | { type: 'cost:alert'; currentCost: number; budgetLimit: number }
  | { type: 'error'; message: string; recoverable: boolean }
  | { type: 'iteration:completed'; iterationId: string };
```

**React Hook:**

```typescript
function useIterationProgress(iterationId: string) {
  const [events, setEvents] = useState<IterationEvent[]>([]);
  const [status, setStatus] = useState<IterationStatus>('PENDING');
  
  useEffect(() => {
    const eventSource = new EventSource(`/api/iterations/${iterationId}/stream`);
    
    eventSource.onmessage = (event) => {
      const data: IterationEvent = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
      
      if (data.type === 'status:changed') {
        setStatus(data.status);
      }
    };
    
    eventSource.onerror = () => {
      eventSource.close();
    };
    
    return () => {
      eventSource.close();
    };
  }, [iterationId]);
  
  return { events, status };
}
```

### **FR-EE-003: Pause/Resume Iteration**

**Priority:** P1 (Should Have)

**Acceptance Criteria:**

- “Pause” button visible during execution
- Pausing:
  - Stops accepting new jobs
  - Allows running jobs to complete
  - Saves state (partial progress preserved)
  - Shows “Paused” status
- Resuming:
  - Continues from last checkpoint
  - Re-queues pending jobs
  - Shows “Resuming…” status
- Cannot pause during critical operations (aggregation, refinement)

**Implementation:**

```typescript
async function pauseIteration(iterationId: string): Promise<void> {
  const iteration = await prisma.iteration.findUniqueOrThrow({
    where: { id: iterationId },
  });
  
  if (!['EXECUTING', 'JUDGING'].includes(iteration.status)) {
    throw new Error('Can only pause during execution or judging');
  }
  
  // Mark as paused
  await prisma.iteration.update({
    where: { id: iterationId },
    data: { status: 'PAUSED' },
  });
  
  // Stop accepting new jobs
  // (Workers check iteration status before starting jobs)
  
  // Publish event
  await redis.publish(`iteration:${iterationId}`, JSON.stringify({
    type: 'status:changed',
    status: 'PAUSED',
  }));
}

async function resumeIteration(iterationId: string): Promise<void> {
  const iteration = await prisma.iteration.findUniqueOrThrow({
    where: { id: iterationId },
    include: {
      modelRuns: { where: { status: 'PENDING' } },
    },
  });
  
  if (iteration.status !== 'PAUSED') {
    throw new Error('Iteration is not paused');
  }
  
  // Determine which phase to resume
  const hasRunsCompleted = await prisma.modelRun.count({
    where: { iterationId, status: 'COMPLETED' },
  }) > 0;
  
  if (iteration.modelRuns.length > 0) {
    // Resume execution
    await prisma.iteration.update({
      where: { id: iterationId },
      data: { status: 'EXECUTING' },
    });
    
    // Re-queue pending runs
    await Promise.all(
      iteration.modelRuns.map((run) =>
        executeQueue.add('execute-run', { modelRunId: run.id })
      )
    );
  } else if (hasRunsCompleted) {
    // Resume judging
    await prisma.iteration.update({
      where: { id: iterationId },
      data: { status: 'JUDGING' },
    });
    
    // Re-trigger judging
    await judgeQueue.add('judge-outputs', { iterationId });
  }
  
  // Publish event
  await redis.publish(`iteration:${iterationId}`, JSON.stringify({
    type: 'status:changed',
    status: 'EXECUTING',
  }));
}
```

### **FR-EE-004: Cancel Iteration**

**Priority:** P1 (Should Have)

**Acceptance Criteria:**

- “Cancel” button (requires confirmation)
- Cancelling:
  - Stops all running jobs
  - Marks iteration as CANCELLED
  - Preserves partial results (don’t delete)
  - Cannot be resumed
- Confirmation dialog shows:
  - Progress so far
  - Cost spent
  - Warning: “This cannot be undone”

-----

## **3.6 Results Viewing**

### **FR-RV-001: Iteration Dashboard**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to see a summary of iteration results so I can understand performance.

**UI Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Iteration #3 Results                   Completed 5m ago │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  KPI Cards                                                │
│  ┌────────────┬────────────┬────────────┬────────────┐  │
│  │ Composite  │ Δ vs Prev  │ Win Rate   │ Cost       │  │
│  │ Score      │            │ (Pairwise) │            │  │
│  ├────────────┼────────────┼────────────┼────────────┤  │
│  │  8.2/10    │  +0.5 ⬆    │   67%      │  $2.34     │  │
│  │ [████████░]│  (+6.5%)   │  ▲ Top     │            │  │
│  └────────────┴────────────┴────────────┴────────────┘  │
│                                                           │
│  Score Breakdown by Model                                │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Model          Composite  95% CI      Tokens  Cost  ││
│  ├─────────────────────────────────────────────────────┤│
│  │ GPT-4o          8.5      [8.2, 8.8]   45K    $2.25  ││
│  │ Claude Sonnet   8.2      [7.9, 8.5]   42K    $1.26  ││
│  │ GPT-4o-mini     7.8      [7.5, 8.1]   38K    $0.11  ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  Score Trend                                             │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 10 ┤                                              ╭─ ││
│  │  9 ┤                                     ╭────╮  │  ││
│  │  8 ┤                   ╭────╮  ╭────╮  │    │  │  ││
│  │  7 ┤      ╭────╮  ╭───│    ╰──╯    ╰──╯    ╰──╯  ││
│  │  6 ┤ ╭────╯    ╰──╯                              ││
│  │    └┴────┴────┴────┴────┴────┴────┴────┴────┴──  ││
│  │     1    2    3    4    5    6    7    8    9     ││
│  │                    Iteration                       ││
│  └─────────────────────────────────────────────────────┘│
│                                                           │
│  [View Outputs →] [Review Refinements →]                 │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

- Shows composite score (weighted average across rubric)
- Shows delta vs. previous iteration (% and absolute)
- Shows 95% confidence interval (bootstrap)
- Shows pairwise win rate (if enabled)
- Shows total cost and tokens for iteration
- Breakdown by model (table)
- Line chart showing score trend across iterations
- Error bars on chart (confidence intervals)
- Links to detailed views

**Metrics Calculation:**

```typescript
interface IterationMetrics {
  compositeScore: number;
  confidenceInterval: { lower: number; upper: number };
  deltaVsPrevious: { absolute: number; percentage: number } | null;
  pairwiseWinRate: number | null;
  totalCost: number;
  totalTokens: number;
  modelScores: {
    modelRunId: string;
    modelName: string;
    compositeScore: number;
    confidenceInterval: { lower: number; upper: number };
    criterionScores: Record<string, number>;
    tokens: number;
    cost: number;
  }[];
  criterionBreakdown: Record<string, {
    avg: number;
    min: number;
    max: number;
    stdDev: number;
  }>;
  facetAnalysis: {
    byTag: Record<string, number>;
    byLength: Record<string, number>;
    byDifficulty: Record<string, number>;
  };
}
```

### **FR-RV-002: Side-by-Side Output Viewer**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to compare outputs from different models side-by-side.

**UI Layout:**

```
┌───────────────────────────────────────────────────────────┐
│  Outputs - Iteration #3                    [Grid ▼] [SxS]│
├───────────────────────────────────────────────────────────┤
│                                                            │
│  Filters: [All Tags ▼] [All Criteria ▼] [All Models ▼]   │
│  Sort: [Best to Worst ▼]                                  │
│                                                            │
│  Test Case 1 of 50                           ← →          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Input:                                              │  │
│  │ {                                                   │  │
│  │   "question": "How do I reset my password?",       │  │
│  │   "context": "User logged out"                     │  │
│  │ }                                                   │  │
│  │                                                     │  │
│  │ Tags: [password] [authentication]                  │  │
│  │ Difficulty: ●●○○○ (2/5)                            │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────┬─────────────────────────────┐   │
│  │ GPT-4o              │ Claude Sonnet 4             │   │
│  │ Score: 8.5/10       │ Score: 8.2/10               │   │
│  ├─────────────────────┼─────────────────────────────┤   │
│  │                     │                             │   │
│  │ To reset your pass- │ I understand you need to    │   │
│  │ word, please follow │ reset your password. Here's │   │
│  │ these steps:        │ what to do:                 │   │
│  │                     │                             │   │
│  │ 1. Go to the login  │ Click "Forgot Password?"    │   │
│  │    page             │ on the login screen. We'll  │   │
│  │ 2. Click "Forgot... │ email you a reset link...   │   │
│  │                     │                             │   │
│  │ [Expand ▼]          │ [Expand ▼]                  │   │
│  └─────────────────────┴─────────────────────────────┘   │
│                                                            │
│  ┌─────────────────────┬─────────────────────────────┐   │
│  │ GPT-4o-mini         │ [Add Model to Compare]      │   │
│  │ Score: 7.8/10       │                             │   │
│  ├─────────────────────┤                             │   │
│  │ You can reset your  │                             │   │
│  │ password by going   │                             │   │
│  │ to the login page   │                             │   │
│  │ and clicking...     │                             │   │
│  └─────────────────────┴─────────────────────────────┘   │
│                                                            │
│  Judge Rationales (click to expand)                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ▶ Helpfulness  ▶ Empathy  ▶ Accuracy  ▶ Concise    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

- Shows 2-4 model outputs side-by-side
- Sticky header with input details
- Collapsible full outputs (truncate to 200 chars initially)
- Score badges prominently displayed
- Navigate between test cases (prev/next buttons)
- Filter by tags, criterion, model
- Sort by best/worst score, alphabetical
- Judge rationales expandable per criterion
- Highlight differences (optional, advanced)
- Copy output to clipboard button
- Flag output for review button

**Performance:**

- Lazy load outputs (virtual scrolling)
- Cache rendered outputs
- Debounce filter changes

### **FR-RV-003: Criterion-Level Analysis**

**Priority:** P1 (Should Have)

**UI:** Tabs/sections for each rubric criterion showing:

- Distribution chart (histogram of scores)
- Top/bottom performers for that criterion
- Example outputs at different score levels
- Judge agreement visualization (inter-rater reliability)

### **FR-RV-004: Facet Analysis**

**Priority:** P1 (Should Have)

**UI:** Heatmap showing performance across facets:

```
┌────────────────────────────────────────────┐
│  Performance Heatmap                        │
├────────────────────────────────────────────┤
│                                             │
│         Model 1  Model 2  Model 3          │
│  Tag A   ████     ███      ██              │
│  Tag B   ███      ████     ███             │
│  Tag C   ██       ███      ████            │
│                                             │
│  XS      ████     ████     ███             │
│  S       ████     ███      ███             │
│  M       ███      ████     ████            │
│  L       ██       ███      ███             │
│  XL      █        ██       ██              │
│                                             │
│  Easy    ████     ████     ████            │
│  Medium  ███      ███      ████            │
│  Hard    ██       ██       ███             │
│                                             │
└────────────────────────────────────────────┘
```

-----

## **3.7 Prompt Refinement**

### **FR-PR-001: Generate Refinement Suggestion**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want the system to propose improvements to my prompt based on test results.

**Trigger:** Automatically after aggregation phase completes.

**Process:**

1. Identify weak criteria (bottom 2 by avg score)
1. Extract failing exemplars (outputs with low scores on weak criteria)
1. Build refiner prompt with context
1. Call refiner LLM (Claude Sonnet 4 or GPT-4o)
1. Parse response (expect unified diff + note)
1. Validate diff (syntactically correct, not too aggressive)
1. Create Suggestion record
1. Notify user via SSE

**Refiner Prompt Template:**

```
# Prompt Refinement Task

You are an expert prompt engineer. Your task is to propose SMALL, targeted improvements to a prompt based on test results.

## Current Objective
{{experiment_goal}}

## Evaluation Rubric
{{rubric_json}}

## Current Prompt
```

{{current_prompt_text}}

```
## Weak Areas
The prompt scores poorly on these criteria:
{{#each weak_criteria}}
- **{{name}}** (avg score: {{avg_score}}/5): {{description}}
{{/each}}

## Failing Exemplars
Here are cases where the prompt performed poorly on weak criteria:

{{#each failing_exemplars}}
### Example {{@index}}
**Input:**
{{json input}}

**Output:**
{{output}}

**Scores:**
{{json scores}}

**Issues:**
{{#each rationales}}
- {{@key}}: {{this}}
{{/each}}
{{/each}}

## Your Task
Propose SMALL, surgical edits to the prompt to improve performance on the weak criteria.

**Requirements:**
- Keep all existing constraints and requirements
- Make minimal changes (< 10% of text)
- Focus on clarity and specificity for weak criteria
- Do NOT change core structure or intent
- Changes should address the specific issues in failing exemplars

**Output Format:**
Return your response in this EXACT format:

<diff>
--- a/prompt.txt
+++ b/prompt.txt
@@ -1,3 +1,4 @@
 Existing line 1
 Existing line 2
-Line to remove
+Line to add
+Another line to add
 Existing line 3
</diff>

<note>
1-2 paragraph explanation of changes and how they address weak criteria:
- What changed
- Why it should help
- Which criteria it targets
</note>

IMPORTANT: The diff must be a valid unified diff format that can be applied with `patch`.
```

**Diff Validation:**

```typescript
import * as diff from 'diff';

function validateDiff(original: string, unifiedDiff: string): ValidationResult {
  try {
    // Parse patch
    const patches = diff.parsePatch(unifiedDiff);
    
    if (patches.length === 0) {
      return { valid: false, error: 'No patches found in diff' };
    }
    
    if (patches.length > 1) {
      return { valid: false, error: 'Multiple patches not supported' };
    }
    
    // Try to apply
    const result = diff.applyPatch(original, patches[0]);
    
    if (!result) {
      return { valid: false, error: 'Diff cannot be applied' };
    }
    
    // Check size constraints
    const lengthDelta = Math.abs(result.length - original.length);
    const maxDelta = original.length * 0.15; // Max 15% change
    
    if (lengthDelta > maxDelta) {
      return { valid: false, error: 'Changes too aggressive (>15% of text)' };
    }
    
    // Check line count delta
    const originalLines = original.split('\n').length;
    const resultLines = result.split('\n').length;
    const lineDelta = Math.abs(resultLines - originalLines);
    
    if (lineDelta > originalLines * 0.2) {
      return { valid: false, error: 'Too many lines changed (>20%)' };
    }
    
    return { valid: true, result };
  } catch (error) {
    return { valid: false, error: error.message };
  }
}
```

**Guardrails:**

- Max changes: 15% of prompt length
- Max lines changed: 20% of line count
- Cannot remove entire sections (> 5 consecutive lines)
- Cannot change template variables ({{…}})
- Must maintain original structure (no complete rewrites)

### **FR-PR-002: Review Suggestion (HITL)**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to review proposed changes before they’re applied.

**UI Layout:**

```
┌───────────────────────────────────────────────────────────┐
│  Review Refinement - Iteration #3                         │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  The refiner proposes these changes to improve:           │
│  • Helpfulness (currently 7.2/10)                         │
│  • Empathy (currently 7.5/10)                             │
│                                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Explanation:                                        │  │
│  │                                                     │  │
│  │ The current prompt is too procedural and lacks     │  │
│  │ empathy cues. These changes:                       │  │
│  │ 1. Add empathetic acknowledgment upfront           │  │
│  │ 2. Soften imperative language                      │  │
│  │ 3. Provide reassurance about the process           │  │
│  │                                                     │  │
│  │ This should improve both Helpfulness (by reducing  │  │
│  │ ambiguity) and Empathy (by acknowledging user      │  │
│  │ frustration).                                       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  Changes (Diff View)                                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │ @@ -1,5 +1,7 @@                                     │  │
│  │  You are a customer support agent.                 │  │
│  │ +When responding, acknowledge the customer's       │  │
│  │ +situation with empathy before providing help.     │  │
│  │                                                     │  │
│  │ -Your task is to answer questions.                 │  │
│  │ +Your goal is to help customers resolve issues     │  │
│  │ +while making them feel heard and supported.       │  │
│  │                                                     │  │
│  │ -Follow these steps:                               │  │
│  │ +Here's how to help effectively:                   │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  Failing Exemplars (Carousel)                             │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Example 1 of 5                          ← →         │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ Input: "I'm locked out and it's urgent!"           │  │
│  │                                                     │  │
│  │ Current Output:                                     │  │
│  │ "To reset your password, go to..."                 │  │
│  │                                                     │  │
│  │ Scores: Helpfulness: 7/10, Empathy: 6/10           │  │
│  │ Issue: Doesn't acknowledge urgency                 │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
│  Actions                                                   │
│  [✓ Approve] [✗ Reject] [✏️ Edit Diff] [+ Add Cases]     │
│                                                            │
│  Keyboard: . = approve, , = reject, E = edit              │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**

- Shows diff with syntax highlighting
- Shows explanation (refiner’s note)
- Shows failing exemplars (carousel, up to 10)
- Three actions:
  - **Approve**: Apply diff, create new prompt version
  - **Reject**: Discard suggestion, log reason
  - **Edit**: Open Monaco editor with diff, allow manual edits
- Keyboard shortcuts (., ,, E)
- Can add manual counterexamples to dataset
- Can add comment/feedback (stored in audit log)

**Approval Flow:**

```typescript
async function approveSuggestion(
  suggestionId: string,
  userId: string
): Promise<string> {
  const suggestion = await prisma.suggestion.findUniqueOrThrow({
    where: { id: suggestionId },
    include: { promptVersion: true },
  });
  
  // Apply diff
  const patches = diff.parsePatch(suggestion.diffUnified);
  const newText = diff.applyPatch(
    suggestion.promptVersion.text,
    patches[0]
  );
  
  if (!newText) {
    throw new Error('Failed to apply diff');
  }
  
  // Create new prompt version
  const newVersion = await prisma.promptVersion.create({
    data: {
      experimentId: suggestion.promptVersion.experimentId,
      version: suggestion.promptVersion.version + 1,
      parentId: suggestion.promptVersionId,
      text: newText,
      systemText: suggestion.promptVersion.systemText,
      fewShots: suggestion.promptVersion.fewShots,
      toolsSchema: suggestion.promptVersion.toolsSchema,
      changelog: `Applied refinement: ${suggestion.note}`,
      createdBy: userId, // Human approved
    },
  });
  
  // Mark suggestion as applied
  await prisma.suggestion.update({
    where: { id: suggestionId },
    data: { status: 'APPLIED' },
  });
  
  // Create review record
  await prisma.review.create({
    data: {
      suggestionId,
      reviewerId: userId,
      decision: 'APPROVE',
      notes: null,
    },
  });
  
  // Log to audit
  await prisma.auditLog.create({
    data: {
      userId,
      action: 'suggestion.approved',
      entityType: 'suggestion',
      entityId: suggestionId,
      changes: { newVersionId: newVersion.id },
    },
  });
  
  return newVersion.id;
}
```

**Rejection Flow:**

```typescript
async function rejectSuggestion(
  suggestionId: string,
  userId: string,
  reason: string
): Promise<void> {
  await prisma.suggestion.update({
    where: { id: suggestionId },
    data: { status: 'REJECTED' },
  });
  
  await prisma.review.create({
    data: {
      suggestionId,
      reviewerId: userId,
      decision: 'REJECT',
      notes: reason,
    },
  });
  
  await prisma.auditLog.create({
    data: {
      userId,
      action: 'suggestion.rejected',
      entityType: 'suggestion',
      entityId: suggestionId,
      changes: { reason },
    },
  });
}
```

### **FR-PR-003: Manual Prompt Editing**

**Priority:** P0 (Must Have)

**Acceptance Criteria:**

- “Edit” button on any prompt version
- Opens Monaco editor
- Shows current prompt text
- Real-time validation (variable detection, length)
- “Save as New Version” creates new PromptVersion
- Changelog field (required, 10-500 chars)
- Shows diff preview before saving

-----

## **3.8 Iteration Loop**

### **FR-IL-001: Continue to Next Iteration**

**Priority:** P0 (Must Have)  
**User Story:** As a user, I want to continue optimizing until I reach the best prompt.

**Trigger:** After suggestion is approved (new prompt version created).

**Flow:**

1. Check stop rules:

- Max iterations reached?
- Budget exceeded?
- Converged (no improvement for N iterations)?
- No refinement suggestions generated?

1. If should stop → Mark experiment COMPLETED, show final report
1. If should continue → Start new iteration with new prompt version

**Stop Rule Evaluation:**

```typescript
async function shouldStop(experimentId: string): Promise<{ stop: boolean; reason?: string }> {
  const experiment = await prisma.experiment.findUniqueOrThrow({
    where: { id: experimentId },
    include: {
      iterations: {
        orderBy: { number: 'desc' },
        take: 10,
      },
    },
  });
  
  const stopRules = experiment.stopRules as StopRules;
  const lastIteration = experiment.iterations[0];
  
  // Check max iterations
  if (lastIteration.number >= stopRules.maxIterations) {
    return { stop: true, reason: 'Maximum iterations reached' };
  }
  
  // Check budget
  const totalSpend = await getTotalSpend(experiment.projectId);
  if (stopRules.maxBudgetUsd && totalSpend >= stopRules.maxBudgetUsd) {
    return { stop: true, reason: 'Budget limit reached' };
  }
  
  // Check convergence
  const recentIterations = experiment.iterations.slice(0, stopRules.convergenceWindow);
  
  if (recentIterations.length >= stopRules.convergenceWindow) {
    const scores = recentIterations.map(
      (it) => (it.metrics as any).compositeScore
    );
    
    const currentScore = scores[0];
    const maxPrevScore = Math.max(...scores.slice(1));
    
    const delta = currentScore - maxPrevScore;
    const deltaPercent = delta / maxPrevScore;
    
    if (deltaPercent < stopRules.minDeltaThreshold) {
      return { 
        stop: true, 
        reason: `Converged (improvement < ${(stopRules.minDeltaThreshold * 100).toFixed(1)}% for ${stopRules.convergenceWindow} iterations)` 
      };
    }
  }
  
  // Check if refinement failed
  const hasSuggestions = await prisma.suggestion.count({
    where: {
      promptVersion: {
        experiment: { id: experimentId },
      },
      status: 'PENDING',
    },
  }) > 0;
  
  if (stopRules.earlyStoppingConfig?.stopIfNoRefinement && !hasSuggestions) {
    return { stop: true, reason: 'No refinement suggestions generated' };
  }
  
  return { stop: false };
}
```

### **FR-IL-002: Final Report**

**Priority:** P1 (Should Have)

**Displayed When:** Experiment completes (stop rule triggered).

**Contents:**

- Summary: iterations run, total cost, total time
- Best prompt version (highest composite score)
- Performance comparison: first vs. last iteration
- Cost breakdown by phase (execution, judging, refinement)
- Token usage breakdown
- Recommendations:
  - Which model to use in production
  - Any remaining weaknesses
  - Suggested next steps
- Export options:
  - Download as PDF report
  - Download prompt as .txt/.md
  - Download results as CSV
  - Download full bundle (YAML + artifacts)

-----

# **4. Non-Functional Requirements**

## **4.1 Performance**

|Requirement                                |Target                 |Measurement   |
|-------------------------------------------|-----------------------|--------------|
|**API Response Time (p95)**                |< 500ms                |APM monitoring|
|**API Response Time (p99)**                |< 1000ms               |APM monitoring|
|**Database Query Time**                    |< 100ms (p95)          |Query logs    |
|**Page Load Time (First Contentful Paint)**|< 1.5s                 |Lighthouse    |
|**Time to Interactive**                    |< 3s                   |Lighthouse    |
|**LLM API Call Timeout**                   |60s (configurable)     |Adapter layer |
|**Concurrent Iterations**                  |Support 10 simultaneous|Load testing  |
|**Job Processing Throughput**              |100 jobs/minute        |BullMQ metrics|
|**SSE Latency**                            |< 200ms event delivery |Custom metrics|

**Optimization Strategies:**

- Database connection pooling (20 connections)
- Query result caching (Redis, 5 min TTL)
- LLM response caching (content-addressed, 1 hour TTL)
- Prisma query optimization (eager loading, select specific fields)
- Index all foreign keys and commonly queried fields
- Use database-level aggregations (avoid N+1 queries)
- Server Components for initial page loads
- Streaming for large datasets
- Virtual scrolling for long lists
- Debounced search inputs (300ms)
- Optimistic updates for mutations

## **4.2 Scalability**

|Dimension                         |Target|Strategy                   |
|----------------------------------|------|---------------------------|
|**Users per Project**             |100   |Validated in tests         |
|**Experiments per Project**       |1,000 |Pagination + archiving     |
|**Prompt Versions per Experiment**|100   |Normal use case            |
|**Test Cases per Dataset**        |10,000|Batched processing         |
|**Iterations per Experiment**     |100   |Stop rules enforce this    |
|**Concurrent Job Workers**        |10    |Horizontally scalable      |
|**Database Size**                 |100 GB|PostgreSQL handles well    |
|**Redis Memory**                  |4 GB  |Typical for caching + queue|

**Scaling Path:**

- **Vertical**: Start with 8 CPU / 16 GB RAM server
- **Horizontal Workers**: Add worker processes as needed
- **Database**: PostgreSQL read replicas for heavy read workloads
- **Redis**: Redis Cluster if queue grows large
- **File Storage**: Migrate to S3 if dataset files exceed local disk

## **4.3 Reliability**

|Requirement             |Target                         |Implementation       |
|------------------------|-------------------------------|---------------------|
|**System Uptime**       |99.5%                          |Monitoring + alerts  |
|**Job Retry Logic**     |3 attempts, exponential backoff|BullMQ built-in      |
|**Data Loss Prevention**|Zero data loss on failure      |Database transactions|
|**Error Recovery**      |Auto-retry transient errors    |Graceful degradation |
|**Backup Frequency**    |Daily (automated)              |PostgreSQL pg_dump   |
|**Backup Retention**    |30 days                        |Automated cleanup    |

**Error Handling:**

- All async operations wrapped in try-catch
- Database operations in transactions
- Failed jobs move to dead-letter queue
- Transient LLM API errors auto-retry (3x)
- Non-transient errors logged + user notified
- Partial iteration results preserved on failure
- Graceful degradation (e.g., if judging fails, still show executions)

## **4.4 Security**

### **Authentication & Authorization**

|Requirement             |Implementation                                         |
|------------------------|-------------------------------------------------------|
|**Password Storage**    |bcrypt (cost: 12)                                      |
|**JWT Signing**         |RS256 (2048-bit key)                                   |
|**JWT Expiry**          |7 days (30 with “remember me”)                         |
|**JWT Storage**         |HTTP-only, Secure, SameSite=Strict cookie              |
|**Session Invalidation**|Logout clears token, no server-side session store in v1|
|**API Key Encryption**  |libsodium sealed box (X25519 + XSalsa20-Poly1305)      |
|**HTTPS Enforcement**   |Required in production                                 |
|**CORS Policy**         |Strict (same-origin only)                              |
|**CSP Policy**          |`default-src 'self'; script-src 'self'`                |

### **Input Validation**

- All API inputs validated with Zod schemas
- SQL injection: Prevented by Prisma parameterization
- XSS: Prevented by React escaping + CSP
- CSRF: Token-based (double-submit cookie pattern)
- File uploads: MIME type + size validation
- Rate limiting: 100 req/min per IP (Cloudflare or nginx)

### **Data Privacy**

- API keys encrypted at rest
- Prompts/outputs stored in plaintext (no PGP in v1)
- Optional: PII detection strips sensitive data before storage
- Audit logs track all data access
- No telemetry/analytics sent to external services
- Self-hosted: user owns all data

### **Vulnerability Management**

- Dependencies scanned weekly (`npm audit`)
- Docker base images updated monthly
- Security patches applied within 7 days
- Penetration testing before v1 release (manual)

## **4.5 Observability**

### **Logging**

**Structured JSON Logs (Pino):**

```typescript
logger.info({
  action: 'iteration.started',
  experimentId: '...',
  userId: '...',
  timestamp: new Date().toISOString(),
  metadata: { /* ... */ },
});
```

**Log Levels:**

- ERROR: System failures, job crashes
- WARN: Recoverable errors, quota warnings
- INFO: Business events (iteration started, prompt created)
- DEBUG: Detailed execution flow (dev only)

**Log Retention:**

- 7 days in active logs
- 90 days in archives (compressed)

### **Metrics (OpenTelemetry)**

**Key Metrics:**

- Request rate, error rate, latency (p50/p95/p99)
- Job queue depth, processing rate, failure rate
- Database connection pool usage
- Redis memory usage
- LLM API call count, latency, cost
- Cache hit rate
- Iteration completion time

**Dashboards:**

- System health (CPU, memory, disk)
- API performance (response times, errors)
- Job queue status
- Cost tracking (per project, per experiment)

### **Tracing**

**Distributed Traces:**

- Trace ID propagated through all services
- Spans: API request → Service → Database query → LLM call
- Visualize in Jaeger/Honeycomb/Datadog

**Instrumented Operations:**

- HTTP requests (incoming/outgoing)
- Database queries
- Redis operations
- LLM API calls
- Job execution

### **Alerts**

**Critical Alerts (PagerDuty/Email):**

- Database connection pool exhausted
- Redis out of memory
- Job queue backing up (> 1000 pending)
- Error rate > 5% for 5 minutes
- Disk usage > 90%

**Warning Alerts (Email):**

- Budget 80% utilized
- Slow queries (> 1s)
- High latency (p95 > 1s)

## **4.6 Usability**

|Requirement                 |Target                       |Validation        |
|----------------------------|-----------------------------|------------------|
|**Time to First Experiment**|< 15 minutes                 |User testing      |
|**Clicks to Run Iteration** |< 3 clicks                   |UX audit          |
|**Loading States**          |All async ops show progress  |Manual testing    |
|**Error Messages**          |Clear, actionable            |Content review    |
|**Help Documentation**      |Inline tooltips + help center|Manual review     |
|**Mobile Responsive**       |Usable on tablet (768px+)    |Responsive testing|

**UX Principles:**

- **Progressive Disclosure**: Hide complexity behind “Advanced” toggles
- **Defaults**: Sensible defaults for all settings
- **Feedback**: Immediate visual feedback for all actions
- **Forgiveness**: Undo/cancel for destructive actions
- **Consistency**: Same patterns across all features

-----

# **5. User Flows & Journeys**

## **5.1 First-Time User Onboarding**

**Goal:** Create first experiment and run first iteration within 15 minutes.

**Steps:**

1. **Sign Up** (2 minutes)

- Navigate to <https://edison.local>
- Click “Sign Up”
- Fill form: email, password, confirm password
- Click “Create Account”
- Redirected to /projects (empty state)

1. **Create Project** (1 minute)

- Click “+ New Project”
- Enter name: “Customer Support Bot”
- Click “Create”
- Redirected to /projects/customer-support-bot

1. **Add API Credentials** (3 minutes)

- Click “Settings” → “Provider Credentials”
- Click “+ Add Credential”
- Select provider: OpenAI
- Enter API key
- Click “Test & Save”
- See success message

1. **Create Experiment** (8 minutes)

- Click “Experiments” → “+ New Experiment”
- **Wizard opens:**
  
  **Step 1: Objective**
- Click “Customer Support” template
- Objective pre-filled, review and edit if needed
- Click “Continue”
  
  **Step 2: Rubric**
- Rubric pre-filled from template
- Adjust weights if desired
- Click “Continue”
  
  **Step 3: Seed Prompt**
- Prompt pre-filled from template
- Read and make small edits
- Click “Continue”
  
  **Step 4: Test Data**
- Click “Generate with AI”
- Domain hints: “customer support inquiries about password resets, billing, and technical issues”
- Count: 20
- Click “Generate”
- Wait 10 seconds
- Preview cases
- Click “Continue”
  
  **Step 5: Models**
- Select: GPT-4o, GPT-4o-mini
- Keep default parameters
- See cost estimate: $0.50-$1.00
- Click “Continue”
  
  **Step 6: Judges**
- Select: GPT-4o, Claude Sonnet 4 (pointwise)
- Enable pairwise: Yes
- Safety: All enabled
- Click “Continue”
  
  **Step 7: Stop Rules**
- Max iterations: 5
- Budget: $10
- Click “Create Experiment”

1. **Run First Iteration** (1 minute)

- Confirmation dialog appears
- Review cost estimate
- Click “Create & Run”
- Redirected to live iteration view

1. **Watch Progress** (5-10 minutes actual runtime)

- See real-time progress timeline
- Watch execution complete
- See judging complete
- See aggregation complete
- See refinement suggestion generated

1. **Review & Approve** (2 minutes)

- Review queue shows 1 suggestion
- Click to review
- Read explanation
- View diff
- View failing exemplars
- Click “Approve”
- Iteration 2 starts automatically

**Success Criteria:**

- User successfully creates and runs experiment
- First iteration completes without errors
- User understands results and next steps

## **5.2 Daily Power User Flow**

**Persona:** ML Engineer optimizing production prompt.

**Goals:**

- Refine existing prompt
- Compare new model vs. current production
- Deploy winner to production (outside Edison)

**Steps:**

1. Log in
1. Navigate to existing experiment
1. Create new prompt version manually:

- Click “Prompts” → latest version → “Edit”
- Make targeted changes
- Save with changelog: “Improved tone and clarity”

1. Add new model config:

- Click “Models” → “+ Add Model”
- Select Claude Opus 4.1
- Save

1. Run iteration with new prompt + new model
1. Compare results:

- View side-by-side outputs
- Filter by difficult cases
- Check facet analysis

1. Decide on winner:

- Claude Opus 4.1 scores 0.3 points higher
- But costs 3x more
- Decide GPT-4o is still better value

1. Mark GPT-4o prompt version as “Production”
1. Export prompt:

- Click “Export” → “Download Prompt as Markdown”
- Copy to production codebase
- Deploy via CI/CD (outside Edison)

-----

# **6. UI/UX Specifications**

## **6.1 Design Tokens**

```typescript
// tailwind.config.ts
export default {
  theme: {
    colors: {
      // Base
      bg: '#FFFFFF',
      'bg-dark': '#0B0C0E',
      ink: '#0F172A',
      'ink-muted': '#475569',
      'ink-subtle': '#94A3B8',
      
      // Primary
      primary: '#0F172A',
      'primary-hover': '#1E293B',
      'primary-active': '#334155',
      
      // Accent
      accent: '#14B8A6',
      'accent-hover': '#0D9488',
      'accent-active': '#0F766E',
      
      // Focus
      focus: '#6366F1',
      
      // Semantic
      success: '#16A34A',
      'success-bg': '#DCFCE7',
      warning: '#F59E0B',
      'warning-bg': '#FEF3C7',
      error: '#EF4444',
      'error-bg': '#FEE2E2',
      info: '#0EA5E9',
      'info-bg': '#E0F2FE',
      
      // Surfaces
      surface: '#F8FAFC',
      'surface-hover': '#F1F5F9',
      border: '#E2E8F0',
      'border-strong': '#CBD5E1',
    },
    
    spacing: {
      0: '0',
      1: '0.25rem',   // 4px
      2: '0.5rem',    // 8px
      3: '0.75rem',   // 12px
      4: '1rem',      // 16px
      5: '1.25rem',   // 20px
      6: '1.5rem',    // 24px
      8: '2rem',      // 32px
      10: '2.5rem',   // 40px
      12: '3rem',     // 48px
      16: '4rem',     // 64px
      20: '5rem',     // 80px
      24: '6rem',     // 96px
    },
    
    borderRadius: {
      sm: '0.25rem',   // 4px
      md: '0.375rem',  // 6px
      lg: '0.5rem',    // 8px
      xl: '0.75rem',   // 12px
      '2xl': '1rem',   // 16px
      '3xl': '1.5rem', // 24px
      full: '9999px',
    },
    
    boxShadow: {
      xs: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      sm: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
      md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
      lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
      xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
    },
    
    fontSize: {
      xs: ['0.75rem', { lineHeight: '1rem' }],     // 12px
      sm: ['0.875rem', { lineHeight: '1.25rem' }], // 14px
      base: ['1rem', { lineHeight: '1.5rem' }],    // 16px
      lg: ['1.125rem', { lineHeight: '1.75rem' }], // 18px
      xl: ['1.25rem', { lineHeight: '1.75rem' }],  // 20px
      '2xl': ['1.5rem', { lineHeight: '2rem' }],   // 24px
      '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
      '4xl': ['2.25rem', { lineHeight: '2.5rem' }],   // 36px
    },
    
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      display: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Menlo', 'monospace'],
    },
  },
};
```

## **6.2 Component Library**

### **Button**

**Variants:**

- `primary`: Solid accent background, white text
- `secondary`: Outline, accent border
- `ghost`: Transparent, hover background
- `danger`: Red background, white text

**Sizes:**

- `sm`: 32px height, 12px font
- `md`: 40px height, 14px font (default)
- `lg`: 48px height, 16px font

**States:**

- Default
- Hover (darken 10%)
- Active (darken 20%)
- Focus (ring)
- Disabled (opacity 50%, cursor not-allowed)
- Loading (spinner, disabled)

**Accessibility:**

- Always has visible focus ring
- Disabled buttons have `aria-disabled="true"`
- Loading buttons have `aria-busy="true"`

### **Input**

**Types:**

- Text, email, password, number, textarea
- Select, multi-select
- Checkbox, radio
- File upload

**States:**

- Default
- Focus (blue ring)
- Error (red border + error message below)
- Disabled
- Read-only

**Validation:**

- Real-time on blur
- Inline error messages
- Success checkmark (optional)

### **Card**

**Structure:**

```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
  <CardFooter>
    {/* Actions */}
  </CardFooter>
</Card>
```

**Variants:**

- Default: white background, border
- Elevated: shadow-md
- Flat: no border, surface background

### **Modal/Dialog**

**Structure:**

```tsx
<Dialog open={open} onOpenChange={setOpen}>
  <DialogTrigger asChild>
    <Button>Open</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Title</DialogTitle>
      <DialogDescription>Description</DialogDescription>
    </DialogHeader>
    {/* Content */}
    <DialogFooter>
      <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
      <Button onClick={handleConfirm}>Confirm</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**Behavior:**

- Backdrop dims page (opacity 80%)
- Click outside to close (configurable)
- Escape key closes
- Focus trap within dialog
- Return focus to trigger on close

### **Toast Notifications**

**Variants:**

- `success`: Green icon + border
- `error`: Red icon + border
- `warning`: Yellow icon + border
- `info`: Blue icon + border

**Position:** Top-right corner (configurable)

**Duration:**

- Success/info: 4 seconds
- Warning: 6 seconds
- Error: 8 seconds (or manual dismiss)

**Stacking:** Maximum 3 visible, queue additional

### **Skeleton Loaders**

**Usage:** Show instead of spinners for loading states.

**Patterns:**

- Card skeleton (for lists)
- Table row skeleton
- Text line skeleton
- Chart skeleton

**Animation:** Shimmer effect (gradient moving left-to-right)

## **6.3 Responsive Breakpoints**

|Breakpoint|Min Width|Target Device   |
|----------|---------|----------------|
|`xs`      |0px      |Mobile portrait |
|`sm`      |640px    |Mobile landscape|
|`md`      |768px    |Tablet portrait |
|`lg`      |1024px   |Tablet landscape|
|`xl`      |1280px   |Desktop         |
|`2xl`     |1536px   |Large desktop   |

**Mobile Behavior:**

- Navigation collapses to hamburger menu (< md)
- Tables become vertically stacked cards (< lg)
- Side-by-side viewer becomes tabbed interface (< lg)
- Wizard step labels hidden on mobile (< sm)

## **6.4 Animation Guidelines**

**Principles:**

- Subtle, not distracting
- Purposeful (communicate state change)
- Respectful of `prefers-reduced-motion`

**Durations:**

- Micro-interactions: 150ms (hover, focus)
- State changes: 250ms (expand, collapse)
- Page transitions: 350ms (fade, slide)

**Easing:**

- Entrances: `ease-out` (start fast, slow down)
- Exits: `ease-in` (start slow, speed up)
- Interactive: `ease-in-out` (smooth both ways)

**Framer Motion Presets:**

```typescript
const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.25 },
};

const slideUp = {
  initial: { y: 20, opacity: 0 },
  animate: { y: 0, opacity: 1 },
  exit: { y: -20, opacity: 0 },
  transition: { duration: 0.3 },
};

const scaleIn = {
  initial: { scale: 0.95, opacity: 0 },
  animate: { scale: 1, opacity: 1 },
  transition: { duration: 0.2 },
};
```

-----


# **7. API Specifications**

## **7.1 tRPC Router Structure**

```typescript
// packages/api/src/trpc/routers/_app.ts
export const appRouter = router({
  auth: authRouter,
  user: userRouter,
  project: projectRouter,
  provider: providerRouter,
  experiment: experimentRouter,
  prompt: promptRouter,
  dataset: datasetRouter,
  model: modelRouter,
  judge: judgeRouter,
  run: runRouter,
  iteration: iterationRouter,
  judgment: judgmentRouter,
  suggestion: suggestionRouter,
  review: reviewRouter,
  aiAssist: aiAssistRouter,
  export: exportRouter,
  analytics: analyticsRouter,
});

export type AppRouter = typeof appRouter;
```

## **7.2 Complete Procedure Specifications**

### **Auth Router**

```typescript
// packages/api/src/trpc/routers/auth.router.ts
export const authRouter = router({
  // POST /api/trpc/auth.register
  register: publicProcedure
    .input(z.object({
      email: z.string().email().max(255),
      password: z.string().min(12).max(128),
      name: z.string().min(1).max(255).optional(),
    }))
    .output(z.object({
      user: z.object({
        id: z.string(),
        email: z.string(),
        name: z.string().nullable(),
      }),
      token: z.string(),
    }))
    .mutation(async ({ input, ctx }) => {
      // Check if email exists
      const existing = await ctx.prisma.user.findUnique({
        where: { email: input.email },
      });
      
      if (existing) {
        throw new TRPCError({
          code: 'CONFLICT',
          message: 'Email already registered',
        });
      }
      
      // Hash password
      const passwordHash = await bcrypt.hash(input.password, 12);
      
      // Create user
      const user = await ctx.prisma.user.create({
        data: {
          email: input.email,
          name: input.name,
          passwordHash,
          role: 'EDITOR',
        },
      });
      
      // Generate JWT
      const token = jwt.sign(
        {
          sub: user.id,
          email: user.email,
          role: user.role,
        },
        process.env.JWT_SECRET!,
        { expiresIn: '7d' }
      );
      
      // Log
      await ctx.prisma.auditLog.create({
        data: {
          userId: user.id,
          action: 'user.registered',
          entityType: 'user',
          entityId: user.id,
        },
      });
      
      return {
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
        },
        token,
      };
    }),

  // POST /api/trpc/auth.login
  login: publicProcedure
    .input(z.object({
      email: z.string().email(),
      password: z.string(),
      rememberMe: z.boolean().default(false),
    }))
    .output(z.object({
      user: z.object({
        id: z.string(),
        email: z.string(),
        name: z.string().nullable(),
      }),
      token: z.string(),
    }))
    .mutation(async ({ input, ctx }) => {
      // Rate limiting check
      const attempts = await ctx.redis.get(`login_attempts:${input.email}`);
      if (attempts && parseInt(attempts) >= 5) {
        throw new TRPCError({
          code: 'TOO_MANY_REQUESTS',
          message: 'Too many failed login attempts. Try again in 15 minutes.',
        });
      }
      
      // Find user
      const user = await ctx.prisma.user.findUnique({
        where: { email: input.email },
      });
      
      if (!user) {
        // Increment attempts
        await ctx.redis.incr(`login_attempts:${input.email}`);
        await ctx.redis.expire(`login_attempts:${input.email}`, 900); // 15 min
        
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Invalid email or password',
        });
      }
      
      // Verify password
      const valid = await bcrypt.compare(input.password, user.passwordHash);
      
      if (!valid) {
        await ctx.redis.incr(`login_attempts:${input.email}`);
        await ctx.redis.expire(`login_attempts:${input.email}`, 900);
        
        throw new TRPCError({
          code: 'UNAUTHORIZED',
          message: 'Invalid email or password',
        });
      }
      
      // Clear attempts
      await ctx.redis.del(`login_attempts:${input.email}`);
      
      // Generate JWT
      const expiresIn = input.rememberMe ? '30d' : '7d';
      const token = jwt.sign(
        {
          sub: user.id,
          email: user.email,
          role: user.role,
        },
        process.env.JWT_SECRET!,
        { expiresIn }
      );
      
      // Log
      await ctx.prisma.auditLog.create({
        data: {
          userId: user.id,
          action: 'user.login',
          entityType: 'user',
          entityId: user.id,
        },
      });
      
      return {
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
        },
        token,
      };
    }),

  // GET /api/trpc/auth.me
  me: protectedProcedure
    .output(z.object({
      id: z.string(),
      email: z.string(),
      name: z.string().nullable(),
      role: z.enum(['VIEWER', 'REVIEWER', 'EDITOR', 'ADMIN', 'OWNER']),
    }))
    .query(async ({ ctx }) => {
      return ctx.user;
    }),

  // POST /api/trpc/auth.logout
  logout: protectedProcedure
    .mutation(async ({ ctx }) => {
      // Log
      await ctx.prisma.auditLog.create({
        data: {
          userId: ctx.user.id,
          action: 'user.logout',
          entityType: 'user',
          entityId: ctx.user.id,
        },
      });
      
      return { success: true };
    }),
});
```

### **Experiment Router**

```typescript
// packages/api/src/trpc/routers/experiment.router.ts
export const experimentRouter = router({
  // POST /api/trpc/experiment.create
  create: protectedProcedure
    .input(z.object({
      projectId: z.string(),
      name: z.string().min(1).max(200),
      description: z.string().max(1000).optional(),
      goal: z.string().min(20).max(2000),
      rubric: RubricSchema,
      safetyConfig: SafetyConfigSchema.optional(),
      stopRules: StopRulesSchema,
    }))
    .output(z.object({
      id: z.string(),
      name: z.string(),
      status: z.enum(['DRAFT', 'RUNNING', 'PAUSED', 'COMPLETED', 'ARCHIVED']),
    }))
    .mutation(async ({ input, ctx }) => {
      // Check permissions
      const member = await ctx.prisma.projectMember.findFirst({
        where: {
          projectId: input.projectId,
          userId: ctx.user.id,
          role: { in: ['EDITOR', 'ADMIN', 'OWNER'] },
        },
      });
      
      if (!member) {
        throw new TRPCError({ code: 'FORBIDDEN' });
      }
      
      // Create experiment
      const experiment = await ctx.prisma.experiment.create({
        data: {
          projectId: input.projectId,
          name: input.name,
          description: input.description,
          goal: input.goal,
          rubric: input.rubric,
          safetyConfig: input.safetyConfig || {},
          stopRules: input.stopRules,
          status: 'DRAFT',
        },
      });
      
      // Log
      await ctx.prisma.auditLog.create({
        data: {
          userId: ctx.user.id,
          action: 'experiment.created',
          entityType: 'experiment',
          entityId: experiment.id,
        },
      });
      
      return {
        id: experiment.id,
        name: experiment.name,
        status: experiment.status,
      };
    }),

  // GET /api/trpc/experiment.get
  get: protectedProcedure
    .input(z.object({ id: z.string() }))
    .output(ExperimentDetailSchema)
    .query(async ({ input, ctx }) => {
      const experiment = await ctx.prisma.experiment.findUnique({
        where: { id: input.id },
        include: {
          project: {
            include: {
              members: { where: { userId: ctx.user.id } },
            },
          },
          promptVersions: {
            orderBy: { version: 'desc' },
            take: 10,
          },
          iterations: {
            orderBy: { number: 'desc' },
            take: 10,
            include: {
              promptVersion: true,
            },
          },
          modelConfigs: { where: { isActive: true } },
          judgeConfigs: { where: { isActive: true } },
        },
      });
      
      if (!experiment || experiment.project.members.length === 0) {
        throw new TRPCError({ code: 'NOT_FOUND' });
      }
      
      return experiment;
    }),

  // GET /api/trpc/experiment.list
  list: protectedProcedure
    .input(z.object({
      projectId: z.string(),
      limit: z.number().int().min(1).max(100).default(20),
      offset: z.number().int().min(0).default(0),
      status: ExperimentStatusSchema.optional(),
      search: z.string().optional(),
    }))
    .output(z.object({
      experiments: z.array(ExperimentListItemSchema),
      total: z.number(),
    }))
    .query(async ({ input, ctx }) => {
      // Check permissions
      const member = await ctx.prisma.projectMember.findFirst({
        where: {
          projectId: input.projectId,
          userId: ctx.user.id,
        },
      });
      
      if (!member) {
        throw new TRPCError({ code: 'FORBIDDEN' });
      }
      
      const where = {
        projectId: input.projectId,
        ...(input.status && { status: input.status }),
        ...(input.search && {
          OR: [
            { name: { contains: input.search, mode: 'insensitive' } },
            { description: { contains: input.search, mode: 'insensitive' } },
          ],
        }),
      };
      
      const [experiments, total] = await Promise.all([
        ctx.prisma.experiment.findMany({
          where,
          orderBy: { updatedAt: 'desc' },
          take: input.limit,
          skip: input.offset,
          include: {
            _count: {
              select: {
                iterations: true,
                promptVersions: true,
              },
            },
          },
        }),
        ctx.prisma.experiment.count({ where }),
      ]);
      
      return { experiments, total };
    }),

  // POST /api/trpc/experiment.update
  update: protectedProcedure
    .input(z.object({
      id: z.string(),
      name: z.string().min(1).max(200).optional(),
      description: z.string().max(1000).optional(),
      goal: z.string().min(20).max(2000).optional(),
      rubric: RubricSchema.optional(),
      stopRules: StopRulesSchema.optional(),
    }))
    .mutation(async ({ input, ctx }) => {
      const { id, ...data } = input;
      
      // Check permissions
      const experiment = await ctx.prisma.experiment.findUniqueOrThrow({
        where: { id },
        include: {
          project: {
            include: {
              members: {
                where: {
                  userId: ctx.user.id,
                  role: { in: ['EDITOR', 'ADMIN', 'OWNER'] },
                },
              },
            },
          },
        },
      });
      
      if (experiment.project.members.length === 0) {
        throw new TRPCError({ code: 'FORBIDDEN' });
      }
      
      // Cannot update running experiment
      if (experiment.status === 'RUNNING') {
        throw new TRPCError({
          code: 'BAD_REQUEST',
          message: 'Cannot update running experiment',
        });
      }
      
      // Update
      const updated = await ctx.prisma.experiment.update({
        where: { id },
        data,
      });
      
      // Log
      await ctx.prisma.auditLog.create({
        data: {
          userId: ctx.user.id,
          action: 'experiment.updated',
          entityType: 'experiment',
          entityId: id,
          changes: data,
        },
      });
      
      return updated;
    }),

  // DELETE /api/trpc/experiment.delete
  delete: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      // Check permissions
      const experiment = await ctx.prisma.experiment.findUniqueOrThrow({
        where: { id: input.id },
        include: {
          project: {
            include: {
              members: {
                where: {
                  userId: ctx.user.id,
                  role: { in: ['ADMIN', 'OWNER'] },
                },
              },
            },
          },
        },
      });
      
      if (experiment.project.members.length === 0) {
        throw new TRPCError({ code: 'FORBIDDEN' });
      }
      
      // Cannot delete running experiment
      if (experiment.status === 'RUNNING') {
        throw new TRPCError({
          code: 'BAD_REQUEST',
          message: 'Cannot delete running experiment. Pause it first.',
        });
      }
      
      // Soft delete (archive)
      await ctx.prisma.experiment.update({
        where: { id: input.id },
        data: { status: 'ARCHIVED' },
      });
      
      // Log
      await ctx.prisma.auditLog.create({
        data: {
          userId: ctx.user.id,
          action: 'experiment.deleted',
          entityType: 'experiment',
          entityId: input.id,
        },
      });
      
      return { success: true };
    }),
});
```

### **Iteration Router**

```typescript
// packages/api/src/trpc/routers/iteration.router.ts
export const iterationRouter = router({
  // POST /api/trpc/iteration.start
  start: protectedProcedure
    .input(z.object({
      experimentId: z.string(),
      promptVersionId: z.string().optional(),
    }))
    .output(z.object({
      iterationId: z.string(),
    }))
    .mutation(async ({ input, ctx }) => {
      // Validate and start iteration
      const iterationId = await ctx.orchestrator.startIteration(
        input.experimentId,
        input.promptVersionId
      );
      
      return { iterationId };
    }),

  // GET /api/trpc/iteration.get
  get: protectedProcedure
    .input(z.object({ id: z.string() }))
    .output(IterationDetailSchema)
    .query(async ({ input, ctx }) => {
      const iteration = await ctx.prisma.iteration.findUniqueOrThrow({
        where: { id: input.id },
        include: {
          experiment: {
            include: {
              project: {
                include: {
                  members: { where: { userId: ctx.user.id } },
                },
              },
            },
          },
          promptVersion: true,
          modelRuns: {
            include: {
              modelConfig: true,
              outputs: {
                include: {
                  case: true,
                  judgments: {
                    include: {
                      judgeConfig: true,
                    },
                  },
                },
              },
            },
          },
        },
      });
      
      // Check permissions
      if (iteration.experiment.project.members.length === 0) {
        throw new TRPCError({ code: 'FORBIDDEN' });
      }
      
      return iteration;
    }),

  // POST /api/trpc/iteration.pause
  pause: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      await ctx.orchestrator.pauseIteration(input.id);
      return { success: true };
    }),

  // POST /api/trpc/iteration.resume
  resume: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      await ctx.orchestrator.resumeIteration(input.id);
      return { success: true };
    }),

  // POST /api/trpc/iteration.cancel
  cancel: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      await ctx.orchestrator.cancelIteration(input.id);
      return { success: true };
    }),
});
```

### **AI Assist Router**

```typescript
// packages/api/src/trpc/routers/aiAssist.router.ts
export const aiAssistRouter = router({
  // POST /api/trpc/aiAssist.draftObjective
  draftObjective: protectedProcedure
    .input(z.object({
      hints: z.string().min(10).max(500),
      count: z.number().int().min(1).max(5).default(3),
    }))
    .output(z.object({
      options: z.array(z.object({
        title: z.string(),
        text: z.string(),
      })),
    }))
    .mutation(async ({ input, ctx }) => {
      const result = await ctx.aiAssist.draftObjectives(
        input.hints,
        input.count
      );
      return result;
    }),

  // POST /api/trpc/aiAssist.draftRubric
  draftRubric: protectedProcedure
    .input(z.object({
      objective: z.string(),
    }))
    .output(z.object({
      criteria: RubricSchema,
    }))
    .mutation(async ({ input, ctx }) => {
      const result = await ctx.aiAssist.draftRubric(input.objective);
      return result;
    }),

  // POST /api/trpc/aiAssist.draftPrompts
  draftPrompts: protectedProcedure
    .input(z.object({
      objective: z.string(),
      rubric: RubricSchema,
      count: z.number().int().min(1).max(5).default(3),
    }))
    .output(z.object({
      prompts: z.array(z.object({
        name: z.string(),
        text: z.string(),
        systemText: z.string().optional(),
        rationale: z.string(),
      })),
    }))
    .mutation(async ({ input, ctx }) => {
      const result = await ctx.aiAssist.draftPrompts(
        input.objective,
        input.rubric,
        input.count
      );
      return result;
    }),

  // POST /api/trpc/aiAssist.improvePrompt
  improvePrompt: protectedProcedure
    .input(z.object({
      promptText: z.string(),
      objective: z.string(),
      focus: z.array(z.string()).optional(),
    }))
    .output(z.object({
      improved: z.string(),
      changes: z.string(),
    }))
    .mutation(async ({ input, ctx }) => {
      const result = await ctx.aiAssist.improvePrompt(
        input.promptText,
        input.objective,
        input.focus
      );
      return result;
    }),

  // POST /api/trpc/aiAssist.generateSynthetic
  generateSynthetic: protectedProcedure
    .input(z.object({
      projectId: z.string(),
      domainHints: z.string(),
      count: z.number().int().min(10).max(500),
      diversity: z.number().min(1).max(10),
      variables: z.array(z.string()),
    }))
    .output(z.object({
      datasetId: z.string(),
    }))
    .mutation(async ({ input, ctx }) => {
      const datasetId = await ctx.generator.generateSyntheticCases({
        projectId: input.projectId,
        spec: {
          domainHints: input.domainHints,
          count: input.count,
          diversity: input.diversity,
          variables: input.variables,
        },
      });
      
      return { datasetId };
    }),
});
```

## **7.3 SSE Endpoints**

### **Iteration Stream**

```typescript
// app/api/iterations/[id]/stream/route.ts
import { NextRequest } from 'next/server';
import { Redis } from 'ioredis';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const iterationId = params.id;
  
  // Verify auth
  const token = request.cookies.get('auth_token')?.value;
  if (!token) {
    return new Response('Unauthorized', { status: 401 });
  }
  
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      
      // Subscribe to Redis pub/sub
      const subscriber = new Redis(process.env.REDIS_URL);
      await subscriber.subscribe(`iteration:${iterationId}`);
      
      // Send initial state
      const iteration = await prisma.iteration.findUnique({
        where: { id: iterationId },
        include: {
          modelRuns: true,
        },
      });
      
      if (iteration) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({
            type: 'initial',
            data: iteration,
          })}\n\n`)
        );
      }
      
      // Listen for events
      subscriber.on('message', (channel, message) => {
        if (channel === `iteration:${iterationId}`) {
          controller.enqueue(encoder.encode(`data: ${message}\n\n`));
        }
      });
      
      // Heartbeat every 15s
      const heartbeat = setInterval(() => {
        controller.enqueue(encoder.encode(': heartbeat\n\n'));
      }, 15000);
      
      // Cleanup on close
      request.signal.addEventListener('abort', () => {
        clearInterval(heartbeat);
        subscriber.unsubscribe();
        subscriber.quit();
        controller.close();
      });
    },
  });
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no', // Disable nginx buffering
    },
  });
}
```

## **7.4 Error Response Format**

All errors follow consistent format:

```typescript
interface ErrorResponse {
  error: {
    code: string;           // TRPC error code
    message: string;        // User-friendly message
    details?: any;          // Additional context
    path?: string;          // Which input field caused error
    timestamp: string;      // ISO 8601 timestamp
    traceId?: string;       // For debugging
  };
}
```

**Error Codes:**

- `UNAUTHORIZED`: Not authenticated
- `FORBIDDEN`: Not authorized for resource
- `NOT_FOUND`: Resource doesn’t exist
- `CONFLICT`: Resource already exists
- `BAD_REQUEST`: Invalid input
- `INTERNAL_SERVER_ERROR`: Unexpected error
- `TOO_MANY_REQUESTS`: Rate limit exceeded
- `TIMEOUT`: Operation timed out

-----

# **8. Data Model Specifications**

## **8.1 Database Indexes**

```sql
-- Performance-critical indexes

-- Projects
CREATE INDEX idx_projects_slug ON projects(slug);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- Project Members
CREATE INDEX idx_project_members_lookup ON project_members(project_id, user_id);
CREATE INDEX idx_project_members_user ON project_members(user_id);

-- Experiments
CREATE INDEX idx_experiments_project_status ON experiments(project_id, status);
CREATE INDEX idx_experiments_updated ON experiments(updated_at DESC);

-- Prompt Versions
CREATE INDEX idx_prompt_versions_experiment_version ON prompt_versions(experiment_id, version DESC);
CREATE INDEX idx_prompt_versions_production ON prompt_versions(experiment_id, is_production) WHERE is_production = true;

-- Iterations
CREATE INDEX idx_iterations_experiment_number ON iterations(experiment_id, number DESC);
CREATE INDEX idx_iterations_status ON iterations(status, scheduled_at) WHERE status IN ('PENDING', 'EXECUTING');

-- Model Runs
CREATE INDEX idx_model_runs_iteration_status ON model_runs(iteration_id, status);

-- Outputs
CREATE INDEX idx_outputs_run_case ON outputs(model_run_id, case_id);

-- Judgments
CREATE INDEX idx_judgments_output_judge ON judgments(output_id, judge_config_id);

-- Cases
CREATE INDEX idx_cases_dataset ON cases(dataset_id);
CREATE INDEX idx_cases_tags ON cases USING GIN(tags);

-- Suggestions
CREATE INDEX idx_suggestions_prompt_status ON suggestions(prompt_version_id, status);

-- Audit Logs
CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action, created_at DESC);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id, created_at DESC);

-- Cost Tracking
CREATE INDEX idx_cost_tracking_project_time ON cost_tracking(project_id, timestamp DESC);
CREATE INDEX idx_cost_tracking_provider ON cost_tracking(provider, model_id, timestamp DESC);
```

## **8.2 Database Constraints**

```sql
-- Business logic constraints

-- Weights must sum to 1.0 (enforced at application layer due to JSON)

-- Positive values only
ALTER TABLE model_runs ADD CONSTRAINT chk_model_runs_tokens_positive 
  CHECK (tokens_in >= 0 AND tokens_out >= 0);

ALTER TABLE model_runs ADD CONSTRAINT chk_model_runs_cost_positive 
  CHECK (cost_usd >= 0);

-- Version numbers are sequential
ALTER TABLE prompt_versions ADD CONSTRAINT chk_prompt_versions_version_positive 
  CHECK (version > 0);

-- Valid status transitions
ALTER TABLE iterations ADD CONSTRAINT chk_iterations_status_valid 
  CHECK (status IN ('PENDING', 'EXECUTING', 'JUDGING', 'AGGREGATING', 'REFINING', 'REVIEWING', 'COMPLETED', 'FAILED', 'CANCELLED', 'PAUSED'));

-- Dates
ALTER TABLE iterations ADD CONSTRAINT chk_iterations_dates 
  CHECK (finished_at IS NULL OR finished_at >= started_at);

ALTER TABLE model_runs ADD CONSTRAINT chk_model_runs_dates 
  CHECK (finished_at IS NULL OR finished_at >= started_at);
```

## **8.3 Soft Delete Pattern**

Instead of hard deletes, use status flags:

```typescript
// Experiments: status = 'ARCHIVED'
// Users: Add deleted_at timestamp (nullable)
// Projects: status = 'ARCHIVED'

// Example query
const activeExperiments = await prisma.experiment.findMany({
  where: {
    projectId,
    status: { not: 'ARCHIVED' },
  },
});
```

## **8.4 Audit Trail**

Every mutation logged:

```typescript
interface AuditLogEntry {
  id: string;
  userId: string | null;        // null for system actions
  action: string;                // 'experiment.created', 'prompt.updated'
  entityType: string;            // 'experiment', 'prompt', 'run'
  entityId: string;
  changes: Record<string, any>; // Old/new values
  metadata: Record<string, any>; // Request IP, user agent, etc.
  createdAt: Date;
}
```

## **8.5 Data Retention Policy**

```typescript
// Configurable per project
interface RetentionPolicy {
  retentionDays: number;          // 0 = keep forever
  archiveAfterDays: number;       // Move to cold storage
  deleteAfterDays: number;        // Hard delete
}

// Default policy
const DEFAULT_RETENTION = {
  retentionDays: 90,
  archiveAfterDays: 365,
  deleteAfterDays: 0, // Never delete
};

// Cleanup job runs daily
async function cleanupOldData() {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - 90);
  
  // Archive old runs
  await prisma.modelRun.updateMany({
    where: {
      finishedAt: { lt: cutoffDate },
      status: 'COMPLETED',
    },
    data: {
      // Move outputs to cold storage (S3 Glacier)
      // Set status to 'ARCHIVED'
    },
  });
}
```

-----

# **9. Business Logic Rules**

## **9.1 Iteration State Machine**

```typescript
type IterationStatus = 
  | 'PENDING'      // Created, not started
  | 'EXECUTING'    // Running model inferences
  | 'JUDGING'      // Evaluating outputs
  | 'AGGREGATING'  // Computing metrics
  | 'REFINING'     // Generating suggestions
  | 'REVIEWING'    // Awaiting human approval
  | 'COMPLETED'    // Finished successfully
  | 'FAILED'       // Error occurred
  | 'CANCELLED'    // User cancelled
  | 'PAUSED';      // User paused

// Valid transitions
const VALID_TRANSITIONS: Record<IterationStatus, IterationStatus[]> = {
  PENDING: ['EXECUTING', 'CANCELLED'],
  EXECUTING: ['JUDGING', 'FAILED', 'PAUSED', 'CANCELLED'],
  JUDGING: ['AGGREGATING', 'FAILED', 'PAUSED', 'CANCELLED'],
  AGGREGATING: ['REFINING', 'COMPLETED', 'FAILED'],
  REFINING: ['REVIEWING', 'COMPLETED', 'FAILED'],
  REVIEWING: ['COMPLETED', 'EXECUTING'], // Approved → next iteration
  COMPLETED: [],
  FAILED: [],
  CANCELLED: [],
  PAUSED: ['EXECUTING', 'JUDGING'], // Resume from where paused
};

function isValidTransition(from: IterationStatus, to: IterationStatus): boolean {
  return VALID_TRANSITIONS[from].includes(to);
}
```

## **9.2 Budget Enforcement**

```typescript
interface BudgetCheck {
  projectId: string;
  maxBudgetUsd: number;
  alertThreshold: number; // 0.0-1.0
}

async function checkBudget(check: BudgetCheck): Promise<BudgetStatus> {
  // Get current spend (last 30 days)
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  
  const result = await prisma.costTracking.aggregate({
    where: {
      projectId: check.projectId,
      timestamp: { gte: thirtyDaysAgo },
    },
    _sum: { costUsd: true },
  });
  
  const currentSpend = result._sum.costUsd || 0;
  const remaining = check.maxBudgetUsd - currentSpend;
  const percentage = currentSpend / check.maxBudgetUsd;
  
  let status: 'OK' | 'WARNING' | 'EXCEEDED';
  
  if (percentage >= 1.0) {
    status = 'EXCEEDED';
  } else if (percentage >= check.alertThreshold) {
    status = 'WARNING';
  } else {
    status = 'OK';
  }
  
  return {
    status,
    currentSpend,
    maxBudget: check.maxBudgetUsd,
    remaining,
    percentage,
  };
}

// Before starting iteration
async function validateBudgetBeforeRun(experimentId: string): Promise<void> {
  const experiment = await prisma.experiment.findUniqueOrThrow({
    where: { id: experimentId },
    include: { project: true },
  });
  
  const stopRules = experiment.stopRules as StopRules;
  
  if (!stopRules.maxBudgetUsd) return; // No budget limit
  
  const budgetStatus = await checkBudget({
    projectId: experiment.projectId,
    maxBudgetUsd: stopRules.maxBudgetUsd,
    alertThreshold: stopRules.budgetAlertThreshold || 0.8,
  });
  
  if (budgetStatus.status === 'EXCEEDED') {
    throw new Error(`Budget exceeded: $${budgetStatus.currentSpend.toFixed(2)} / $${budgetStatus.maxBudget.toFixed(2)}`);
  }
  
  if (budgetStatus.status === 'WARNING') {
    // Send alert but allow to continue
    await sendBudgetAlert(experiment.projectId, budgetStatus);
  }
}
```

## **9.3 Prompt Version Lineage**

```typescript
interface PromptLineage {
  version: number;
  parentId: string | null;
  changelog: string;
  isProduction: boolean;
  createdBy: string | null;
  createdAt: Date;
}

// Get full history of a prompt
async function getPromptHistory(promptVersionId: string): Promise<PromptLineage[]> {
  const history: PromptLineage[] = [];
  let current = await prisma.promptVersion.findUniqueOrThrow({
    where: { id: promptVersionId },
  });
  
  history.push(current);
  
  // Walk up the parent chain
  while (current.parentId) {
    current = await prisma.promptVersion.findUniqueOrThrow({
      where: { id: current.parentId },
    });
    history.push(current);
  }
  
  return history.reverse(); // Oldest first
}

// Compare two versions
async function comparePromptVersions(
  versionAId: string,
  versionBId: string
): Promise<string> {
  const [versionA, versionB] = await Promise.all([
    prisma.promptVersion.findUniqueOrThrow({ where: { id: versionAId } }),
    prisma.promptVersion.findUniqueOrThrow({ where: { id: versionBId } }),
  ]);
  
  const patches = diff.createPatch(
    'prompt.txt',
    versionA.text,
    versionB.text,
    'Version A',
    'Version B'
  );
  
  return patches;
}
```

## **9.4 Concurrency Control**

```typescript
// Prevent concurrent iterations on same experiment
async function acquireExperimentLock(experimentId: string): Promise<boolean> {
  const lockKey = `experiment:${experimentId}:lock`;
  const lockValue = crypto.randomUUID();
  const lockTTL = 3600; // 1 hour
  
  // Try to acquire lock with SET NX EX
  const acquired = await redis.set(
    lockKey,
    lockValue,
    'EX',
    lockTTL,
    'NX'
  );
  
  return acquired === 'OK';
}

async function releaseExperimentLock(experimentId: string): Promise<void> {
  const lockKey = `experiment:${experimentId}:lock`;
  await redis.del(lockKey);
}

// Usage
async function startIteration(experimentId: string): Promise<string> {
  const locked = await acquireExperimentLock(experimentId);
  
  if (!locked) {
    throw new Error('Experiment is already running. Wait for it to complete.');
  }
  
  try {
    // Start iteration...
    const iterationId = await createIteration(experimentId);
    return iterationId;
  } catch (error) {
    await releaseExperimentLock(experimentId);
    throw error;
  }
}
```

## **9.5 Model Configuration Validation**

```typescript
async function validateModelConfig(config: ModelConfig): Promise<void> {
  // Check if provider credential exists and is active
  const credential = await prisma.providerCredential.findFirst({
    where: {
      provider: config.provider,
      isActive: true,
    },
  });
  
  if (!credential) {
    throw new Error(`No active credential for provider: ${config.provider}`);
  }
  
  // Validate model ID is supported by provider
  const adapter = await adapterFactory.getAdapter(credential, config.modelId);
  const isValid = await adapter.validateModel();
  
  if (!isValid) {
    throw new Error(`Model ${config.modelId} not supported by ${config.provider}`);
  }
  
  // Validate parameters
  const params = config.params as ModelParams;
  
  if (params.temperature < 0 || params.temperature > 2) {
    throw new Error('Temperature must be between 0 and 2');
  }
  
  if (params.maxTokens && params.maxTokens < 1) {
    throw new Error('maxTokens must be positive');
  }
  
  // Provider-specific validations
  if (config.provider === 'OPENAI' && params.topK) {
    throw new Error('OpenAI does not support topK parameter');
  }
}
```

-----

# **10. LLM Integration Specifications**

## **10.1 Provider-Specific Implementations**

### **OpenAI Adapter**

```typescript
// packages/api/src/llm/adapters/openai.adapter.ts
import OpenAI from 'openai';
import type { ChatCompletionMessageParam } from 'openai/resources/chat/completions';

export class OpenAIAdapter implements LLMAdapter {
  private client: OpenAI;
  public readonly provider = 'OPENAI';
  
  constructor(
    private apiKey: string,
    public readonly modelId: string,
    private config?: { organization?: string; baseURL?: string }
  ) {
    this.client = new OpenAI({
      apiKey,
      organization: config?.organization,
      baseURL: config?.baseURL,
    });
  }
  
  async chat(
    messages: LLMMessage[],
    options: LLMOptions = {}
  ): Promise<LLMResponse> {
    const cacheKey = this.getCacheKey(messages, options);
    
    // Check cache
    const cached = await redis.get(cacheKey);
    if (cached) {
      const result = JSON.parse(cached);
      return { ...result, cached: true };
    }
    
    const startTime = Date.now();
    
    try {
      const response = await this.client.chat.completions.create({
        model: this.modelId,
        messages: messages as ChatCompletionMessageParam[],
        temperature: options.params?.temperature,
        max_tokens: options.params?.maxTokens,
        top_p: options.params?.topP,
        frequency_penalty: options.params?.frequencyPenalty,
        presence_penalty: options.params?.presencePenalty,
        seed: options.seed,
        tools: options.tools,
        response_format: options.responseFormat,
      });
      
      const result: LLMResponse = {
        text: response.choices[0].message.content || '',
        usage: {
          promptTokens: response.usage?.prompt_tokens || 0,
          completionTokens: response.usage?.completion_tokens || 0,
          totalTokens: response.usage?.total_tokens || 0,
        },
        latencyMs: Date.now() - startTime,
        cached: false,
        model: response.model,
        finishReason: this.mapFinishReason(response.choices[0].finish_reason),
        raw: response,
      };
      
      // Cache for 1 hour
      await redis.setex(cacheKey, 3600, JSON.stringify(result));
      
      // Track usage
      await this.trackUsage(result);
      
      return result;
    } catch (error) {
      if (error instanceof OpenAI.APIError) {
        throw this.mapError(error);
      }
      throw error;
    }
  }
  
  async streamChat(
    messages: LLMMessage[],
    options: LLMOptions = {}
  ): AsyncIterable<LLMStreamChunk> {
    const stream = await this.client.chat.completions.create({
      model: this.modelId,
      messages: messages as ChatCompletionMessageParam[],
      temperature: options.params?.temperature,
      max_tokens: options.params?.maxTokens,
      stream: true,
    });
    
    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content || '';
      if (delta) {
        yield {
          text: delta,
          finishReason: null,
        };
      }
      
      if (chunk.choices[0]?.finish_reason) {
        yield {
          text: '',
          finishReason: this.mapFinishReason(chunk.choices[0].finish_reason),
        };
      }
    }
  }
  
  estimateCost(promptTokens: number, completionTokens: number): number {
    const pricing = this.getPricing();
    return (
      (promptTokens * pricing.input / 1000) +
      (completionTokens * pricing.output / 1000)
    );
  }
  
  private getPricing(): { input: number; output: number } {
    // Pricing per 1K tokens as of 2024
    const pricingTable: Record<string, { input: number; output: number }> = {
      'gpt-4o': { input: 0.0025, output: 0.01 },
      'gpt-4o-mini': { input: 0.00015, output: 0.0006 },
      'gpt-4-turbo': { input: 0.01, output: 0.03 },
      'gpt-4': { input: 0.03, output: 0.06 },
      'gpt-3.5-turbo': { input: 0.0005, output: 0.0015 },
    };
    
    return pricingTable[this.modelId] || { input: 0.001, output: 0.002 };
  }
  
  private getCacheKey(messages: LLMMessage[], options: LLMOptions): string {
    const payload = {
      provider: this.provider,
      model: this.modelId,
      messages,
      params: options.params,
      seed: options.seed,
    };
    
    return `llm:cache:${createHash('sha256').update(JSON.stringify(payload)).digest('hex')}`;
  }
  
  private mapFinishReason(reason: string): LLMFinishReason {
    const mapping: Record<string, LLMFinishReason> = {
      'stop': 'stop',
      'length': 'length',
      'content_filter': 'content_filter',
      'tool_calls': 'tool_calls',
    };
    return mapping[reason] || 'stop';
  }
  
  private mapError(error: OpenAI.APIError): Error {
    if (error.status === 429) {
      return new LLMError('RATE_LIMIT', 'Rate limit exceeded', error);
    }
    if (error.status === 401) {
      return new LLMError('INVALID_KEY', 'Invalid API key', error);
    }
    if (error.status === 500) {
      return new LLMError('PROVIDER_ERROR', 'Provider server error', error);
    }
    return new LLMError('UNKNOWN', error.message, error);
  }
  
  private async trackUsage(response: LLMResponse): Promise<void> {
    // Track in memory for real-time metrics
    await redis.hincrby(`usage:openai:${this.modelId}`, 'promptTokens', response.usage.promptTokens);
    await redis.hincrby(`usage:openai:${this.modelId}`, 'completionTokens', response.usage.completionTokens);
    
    // Set expiry (1 day)
    await redis.expire(`usage:openai:${this.modelId}`, 86400);
  }
}
```

### **Anthropic Adapter**

```typescript
// packages/api/src/llm/adapters/anthropic.adapter.ts
import Anthropic from '@anthropic-ai/sdk';

export class AnthropicAdapter implements LLMAdapter {
  private client: Anthropic;
  public readonly provider = 'ANTHROPIC';
  
  constructor(
    private apiKey: string,
    public readonly modelId: string
  ) {
    this.client = new Anthropic({ apiKey });
  }
  
  async chat(
    messages: LLMMessage[],
    options: LLMOptions = {}
  ): Promise<LLMResponse> {
    const cacheKey = this.getCacheKey(messages, options);
    
    // Check cache
    const cached = await redis.get(cacheKey);
    if (cached) {
      return { ...JSON.parse(cached), cached: true };
    }
    
    const startTime = Date.now();
    
    // Extract system message
    const systemMessage = messages.find(m => m.role === 'system')?.content;
    const conversationMessages = messages
      .filter(m => m.role !== 'system')
      .map(m => ({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: m.content,
      }));
    
    try {
      const response = await this.client.messages.create({
        model: this.modelId,
        max_tokens: options.params?.maxTokens || 4096,
        temperature: options.params?.temperature,
        top_p: options.params?.topP,
        system: systemMessage,
        messages: conversationMessages as any,
      });
      
      const result: LLMResponse = {
        text: response.content[0].type === 'text' ? response.content[0].text : '',
        usage: {
          promptTokens: response.usage.input_tokens,
          completionTokens: response.usage.output_tokens,
          totalTokens: response.usage.input_tokens + response.usage.output_tokens,
        },
        latencyMs: Date.now() - startTime,
        cached: false,
        model: response.model,
        finishReason: this.mapFinishReason(response.stop_reason),
        raw: response,
      };
      
      // Cache
      await redis.setex(cacheKey, 3600, JSON.stringify(result));
      
      return result;
    } catch (error) {
      if (error instanceof Anthropic.APIError) {
        throw this.mapError(error);
      }
      throw error;
    }
  }
  
  estimateCost(promptTokens: number, completionTokens: number): number {
    const pricing = this.getPricing();
    return (
      (promptTokens * pricing.input / 1000000) +
      (completionTokens * pricing.output / 1000000)
    );
  }
  
  private getPricing(): { input: number; output: number } {
    // Pricing per 1M tokens
    const pricingTable: Record<string, { input: number; output: number }> = {
      'claude-opus-4': { input: 15.0, output: 75.0 },
      'claude-opus-4.1': { input: 15.0, output: 75.0 },
      'claude-sonnet-4': { input: 3.0, output: 15.0 },
      'claude-sonnet-4.5': { input: 3.0, output: 15.0 },
      'claude-haiku-4': { input: 0.25, output: 1.25 },
    };
    
    return pricingTable[this.modelId] || { input: 3.0, output: 15.0 };
  }
  
  private mapFinishReason(reason: string | null): LLMFinishReason {
    const mapping: Record<string, LLMFinishReason> = {
      'end_turn': 'stop',
      'max_tokens': 'length',
      'stop_sequence': 'stop',
    };
    return mapping[reason || ''] || 'stop';
  }
  
  private getCacheKey(messages: LLMMessage[], options: LLMOptions): string {
    const payload = {
      provider: this.provider,
      model: this.modelId,
      messages,
      params: options.params,
    };
    return `llm:cache:${createHash('sha256').update(JSON.stringify(payload)).digest('hex')}`;
  }
  
  private mapError(error: Anthropic.APIError): Error {
    if (error.status === 429) {
      return new LLMError('RATE_LIMIT', 'Rate limit exceeded', error);
    }
    if (error.status === 401) {
      return new LLMError('INVALID_KEY', 'Invalid API key', error);
    }
    return new LLMError('UNKNOWN', error.message, error);
  }
}
```

## **10.2 Retry Logic with Exponential Backoff**

```typescript
// packages/api/src/llm/retry.ts
interface RetryConfig {
  maxAttempts: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
  retryableErrors: string[];
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  initialDelayMs: 1000,
  maxDelayMs: 30000,
  backoffMultiplier: 2,
  retryableErrors: ['RATE_LIMIT', 'PROVIDER_ERROR', 'TIMEOUT'],
};

async function withRetry<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const cfg = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: Error;
  
  for (let attempt = 0; attempt < cfg.maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      // Check if error is retryable
      if (error instanceof LLMError && cfg.retryableErrors.includes(error.code)) {
        // Calculate delay
        const delay = Math.min(
          cfg.initialDelayMs * Math.pow(cfg.backoffMultiplier, attempt),
          cfg.maxDelayMs
        );
        
        // Add jitter (±25%)
        const jitter = delay * 0.25 * (Math.random() * 2 - 1);
        const finalDelay = delay + jitter;
        
        logger.warn({
          message: 'Retrying LLM call',
          attempt: attempt + 1,
          maxAttempts: cfg.maxAttempts,
          delayMs: finalDelay,
          error: error.message,
        });
        
        await sleep(finalDelay);
        continue;
      }
      
      // Non-retryable error, throw immediately
      throw error;
    }
  }
  
  // All attempts failed
  throw lastError!;
}

// Usage
const response = await withRetry(() =>
  adapter.chat(messages, options)
);
```

## **10.3 Timeout Handling**

```typescript
async function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  errorMessage: string = 'Operation timed out'
): Promise<T> {
  let timeoutId: NodeJS.Timeout;
  
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new LLMError('TIMEOUT', errorMessage));
    }, timeoutMs);
  });
  
  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    clearTimeout(timeoutId!);
  }
}

// Usage
const response = await withTimeout(
  adapter.chat(messages, options),
  60000, // 60 second timeout
  'LLM API call timed out after 60 seconds'
);
```

## **10.4 Structured Output Parsing**

```typescript
// packages/api/src/llm/structured.ts
import { z } from 'zod';

async function getChatCompletion<T>(
  adapter: LLMAdapter,
  messages: LLMMessage[],
  schema: z.ZodType<T>,
  options: LLMOptions = {}
): Promise<T> {
  // Add JSON formatting instruction to system message
  const systemMessage = messages.find(m => m.role === 'system');
  if (systemMessage) {
    systemMessage.content += '\n\nReturn ONLY valid JSON matching the schema. No markdown, no explanations.';
  } else {
    messages.unshift({
      role: 'system',
      content: 'Return ONLY valid JSON. No markdown, no explanations.',
    });
  }
  
  // Request JSON format (if provider supports)
  const enhancedOptions = {
    ...options,
    responseFormat: { type: 'json_object' },
  };
  
  const response = await adapter.chat(messages, enhancedOptions);
  
  // Extract JSON from response
  let jsonText = response.text.trim();
  
  // Remove markdown code fences if present
  jsonText = jsonText.replace(/```json\n?/g, '').replace(/```\n?/g, '');
  
  // Parse and validate
  try {
    const parsed = JSON.parse(jsonText);
    return schema.parse(parsed);
  } catch (error) {
    logger.error({
      message: 'Failed to parse structured output',
      response: response.text,
      error,
    });
    
    throw new Error(`Failed to parse structured output: ${error.message}`);
  }
}

// Usage
const judgment = await getChatCompletion(
  adapter,
  messages,
  JudgmentResultSchema,
  { params: { temperature: 0.3 } }
);
```

-----

# **11. Security Specifications**

## **11.1 API Key Encryption**

```typescript
// packages/api/src/lib/crypto.ts
import sodium from 'libsodium-wrappers';

// Generate key pair (run once, store in env)
export async function generateKeyPair(): Promise<{ publicKey: string; privateKey: string }> {
  await sodium.ready;
  const keyPair = sodium.crypto_box_keypair();
  
  return {
    publicKey: Buffer.from(keyPair.publicKey).toString('hex'),
    privateKey: Buffer.from(keyPair.privateKey).toString('hex'),
  };
}

// Encrypt API key
export async function encryptApiKey(apiKey: string): Promise<string> {
  await sodium.ready;
  
  const publicKey = Buffer.from(process.env.ENCRYPTION_PUBLIC_KEY!, 'hex');
  const encrypted = sodium.crypto_box_seal(
    Buffer.from(apiKey, 'utf8'),
    publicKey
  );
  
  return Buffer.from(encrypted).toString('base64');
}

// Decrypt API key
export async function decryptApiKey(encrypted: string): Promise<string> {
  await sodium.ready;
  
  const publicKey = Buffer.from(process.env.ENCRYPTION_PUBLIC_KEY!, 'hex');
  const privateKey = Buffer.from(process.env.ENCRYPTION_PRIVATE_KEY!, 'hex');
  
  const decrypted = sodium.crypto_box_seal_open(
    Buffer.from(encrypted, 'base64'),
    publicKey,
    privateKey
  );
  
  return Buffer.from(decrypted).toString('utf8');
}

// Usage
const encrypted = await encryptApiKey('sk-...');
await prisma.providerCredential.create({
  data: {
    encryptedApiKey: encrypted,
    // ...
  },
});

// Later
const decrypted = await decryptApiKey(credential.encryptedApiKey);
const adapter = new OpenAIAdapter(decrypted, modelId);
```

## **11.2 Rate Limiting**

```typescript
// packages/api/src/middleware/rateLimit.ts
import { Redis } from 'ioredis';

interface RateLimitConfig {
  windowMs: number;        // Time window in milliseconds
  maxRequests: number;     // Max requests per window
  keyPrefix: string;       // Redis key prefix
}

class RateLimiter {
  constructor(
    private redis: Redis,
    private config: RateLimitConfig
  ) {}
  
  async checkLimit(identifier: string): Promise<{ allowed: boolean; remaining: number; resetAt: Date }> {
    const key = `${this.config.keyPrefix}:${identifier}`;
    const now = Date.now();
    const windowStart = now - this.config.windowMs;
    
    // Remove old entries
    await this.redis.zremrangebyscore(key, '-inf', windowStart);
    
    // Count requests in current window
    const count = await this.redis.zcount(key, windowStart, '+inf');
    
    if (count >= this.config.maxRequests) {
      const resetAt = new Date(windowStart + this.config.windowMs);
      return { allowed: false, remaining: 0, resetAt };
    }
    
    // Add current request
    await this.redis.zadd(key, now, `${now}-${Math.random()}`);
    await this.redis.expire(key, Math.ceil(this.config.windowMs / 1000));
    
    const remaining = this.config.maxRequests - count - 1;
    const resetAt = new Date(now + this.config.windowMs);
    
    return { allowed: true, remaining, resetAt };
  }
}

// Global rate limiter (per IP)
const globalRateLimiter = new RateLimiter(redis, {
  windowMs: 60 * 1000,  // 1 minute
  maxRequests: 100,
  keyPrefix: 'ratelimit:ip',
});

// Auth rate limiter (per email)
const authRateLimiter = new RateLimiter(redis, {
  windowMs: 15 * 60 * 1000,  // 15 minutes
  maxRequests: 5,
  keyPrefix: 'ratelimit:auth',
});

// Middleware
export function rateLimitMiddleware(
  limiter: RateLimiter,
  getIdentifier: (req: Request) => string
) {
  return async (req: Request, res: Response, next: NextFunction) => {
    const identifier = getIdentifier(req);
    const result = await limiter.checkLimit(identifier);
    
    res.setHeader('X-RateLimit-Limit', limiter.config.maxRequests.toString());
    res.setHeader('X-RateLimit-Remaining', result.remaining.toString());
    res.setHeader('X-RateLimit-Reset', result.resetAt.toISOString());
    
    if (!result.allowed) {
      res.status(429).json({
        error: {
          code: 'TOO_MANY_REQUESTS',
          message: 'Rate limit exceeded',
          resetAt: result.resetAt.toISOString(),
        },
      });
      return;
    }
    
    next();
  };
}
```

## **11.3 Input Sanitization**

```typescript
// packages/api/src/lib/sanitize.ts
import DOMPurify from 'isomorphic-dompurify';

// Sanitize HTML (for rich text fields)
export function sanitizeHtml(input: string): string {
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'code', 'pre'],
    ALLOWED_ATTR: ['href', 'target'],
  });
}

// Sanitize filename
export function sanitizeFilename(filename: string): string {
  return filename
    .replace(/[^a-zA-Z0-9._-]/g, '_')
    .replace(/_{2,}/g, '_')
    .substring(0, 255);
}

// Sanitize for SQL LIKE (escape % and _)
export function sanitizeForLike(input: string): string {
  return input.replace(/[%_]/g, '\\$&');
}

// Strip control characters
export function stripControlChars(input: string): string {
  return input.replace(/[\x00-\x1F\x7F]/g, '');
}
```

## **11.4 CSRF Protection**

```typescript
// packages/api/src/middleware/csrf.ts
import { createHash, randomBytes } from 'crypto';

export function generateCsrfToken(): string {
  return randomBytes(32).toString('hex');
}

export function verifyCsrfToken(token: string, expectedToken: string): boolean {
  if (!token || !expectedToken) return false;
  
  // Constant-time comparison to prevent timing attacks
  const tokenHash = createHash('sha256').update(token).digest('hex');
  const expectedHash = createHash('sha256').update(expectedToken).digest('hex');
  
  return tokenHash === expectedHash;
}

// Middleware
export function csrfMiddleware(req: Request, res: Response, next: NextFunction) {
  // Skip for GET, HEAD, OPTIONS
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
    return next();
  }
  
  const token = req.headers['x-csrf-token'] as string;
  const expectedToken = req.cookies['csrf_token'];
  
  if (!verifyCsrfToken(token, expectedToken)) {
    res.status(403).json({
      error: {
        code: 'INVALID_CSRF_TOKEN',
        message: 'CSRF token validation failed',
      },
    });
    return;
  }
  
  next();
}
```

## **11.5 Content Security Policy**

```typescript
// next.config.js
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' 'unsafe-inline'", // Monaco editor needs unsafe-eval
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "font-src 'self' data:",
      "connect-src 'self' https://api.openai.com https://api.anthropic.com",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; '),
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY',
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff',
  },
  {
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin',
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=()',
  },
];

module.exports = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
};
```

-----

# **12. Error Handling & Recovery**

## **12.1 Error Classification**

```typescript
// packages/api/src/errors/types.ts
export class AppError extends Error {
  constructor(
    public code: string,
    message: string,
    public statusCode: number = 500,
    public details?: any
  ) {
    super(message);
    this.name = 'AppError';
  }
}

// Domain-specific errors
export class ValidationError extends AppError {
  constructor(message: string, details?: any) {
    super('VALIDATION_ERROR', message, 400, details);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string, id?: string) {
    super('NOT_FOUND', `${resource}${id ? ` ${id}` : ''} not found`, 404);
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string = 'Unauthorized') {
    super('UNAUTHORIZED', message, 401);
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string = 'Forbidden') {
    super('FORBIDDEN', message, 403);
    this.name = 'ForbiddenError';
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super('CONFLICT', message, 409);
    this.name = 'ConflictError';
  }
}

export class LLMError extends AppError {
  constructor(
    public llmCode: string,
    message: string,
    public originalError?: any
  ) {
    super('LLM_ERROR', message, 500, { llmCode, originalError });
    this.name = 'LLMError';
  }
}
```

## **12.2 Global Error Handler**

```typescript
// packages/api/src/middleware/errorHandler.ts
import { TRPCError } from '@trpc/server';
import { Prisma } from '@prisma/client';

export function errorHandler(error: Error, req: Request, res: Response, next: NextFunction) {
  const traceId = req.headers['x-trace-id'] || crypto.randomUUID();
  
  // Log error
  logger.error({
    message: error.message,
    stack: error.stack,
    traceId,
    url: req.url,
    method: req.method,
    userId: req.user?.id,
  });
  
  // Map to HTTP response
  if (error instanceof AppError) {
    return res.status(error.statusCode).json({
      error: {
        code: error.code,
        message: error.message,
        details: error.details,
        traceId,
      },
    });
  }
  
  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    // Handle Prisma errors
    if (error.code === 'P2002') {
      return res.status(409).json({
        error: {
          code: 'CONFLICT',
          message: 'Resource already exists',
          traceId,
        },
      });
    }
    
    if (error.code === 'P2025') {
      return res.status(404).json({
        error: {
          code: 'NOT_FOUND',
          message: 'Resource not found',
          traceId,
        },
      });
    }
  }
  
  if (error instanceof TRPCError) {
    return res.status(getStatusFromTRPCCode(error.code)).json({
      error: {
        code: error.code,
        message: error.message,
        traceId,
      },
    });
  }
  
  // Unknown error
  return res.status(500).json({
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'An unexpected error occurred',
      traceId,
    },
  });
}

function getStatusFromTRPCCode(code: string): number {
  const mapping: Record<string, number> = {
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'TIMEOUT': 408,
    'CONFLICT': 409,
    'PRECONDITION_FAILED': 412,
    'PAYLOAD_TOO_LARGE': 413,
    'TOO_MANY_REQUESTS': 429,
    'INTERNAL_SERVER_ERROR': 500,
  };
  
  return mapping[code] || 500;
}
```

## **12.3 Graceful Degradation**

```typescript
// If judging fails, still show execution results
async function handleJudgingFailure(iterationId: string, error: Error): Promise<void> {
  logger.error({
    message: 'Judging failed, marking iteration as partially complete',
    iterationId,
    error,
  });
  
  await prisma.iteration.update({
    where: { id: iterationId },
    data: {
      status: 'COMPLETED',
      metrics: {
        error: 'Judging failed',
        executionCompleted: true,
        judgingFailed: true,
      },
    },
  });
  
  // Notify user
  await sendNotification({
    userId: iteration.experiment.project.members[0].userId,
    type: 'warning',
    title: 'Iteration partially completed',
    message: 'Execution completed successfully, but judging failed. You can review raw outputs.',
  });
}

// If refinement fails, allow manual prompt editing
async function handleRefinementFailure(iterationId: string, error: Error): Promise<void> {
  logger.error({
    message: 'Refinement failed',
    iterationId,
    error,
  });
  
  await prisma.iteration.update({
    where: { id: iterationId },
    data: { status: 'COMPLETED' },
  });
  
  // Notify user
  await sendNotification({
    userId: iteration.experiment.project.members[0].userId,
    type: 'info',
    title: 'Refinement unavailable',
    message: 'Automatic refinement failed. You can manually edit the prompt to continue.',
  });
}
```

## **12.4 Circuit Breaker Pattern**

```typescript
// packages/api/src/lib/circuitBreaker.ts
interface CircuitBreakerConfig {
  failureThreshold: number;    // Number of failures before opening
  successThreshold: number;    // Number of successes to close
  timeout: number;             // Time to wait before trying again (ms)
}

class CircuitBreaker {
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  private failureCount = 0;
  private successCount = 0;
  private nextAttempt = 0;
  
  constructor(private config: CircuitBreakerConfig) {}
  
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttempt) {
        throw new Error('Circuit breaker is OPEN');
      }
      
      // Try to recover
      this.state = 'HALF_OPEN';
      this.successCount = 0;
    }
    
    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }
  
  private onSuccess() {
    this.failureCount = 0;
    
    if (this.state === 'HALF_OPEN') {
      this.successCount++;
      
      if (this.successCount >= this.config.successThreshold) {
        this.state = 'CLOSED';
        this.successCount = 0;
      }
    }
  }
  
  private onFailure() {
    this.failureCount++;
    this.successCount = 0;
    
    if (this.failureCount >= this.config.failureThreshold) {
      this.state = 'OPEN';
      this.nextAttempt = Date.now() + this.config.timeout;
    }
  }
  
  getState() {
    return {
      state: this.state,
      failureCount: this.failureCount,
      successCount: this.successCount,
      nextAttempt: this.nextAttempt,
    };
  }
}

// Usage: Protect external API calls
const openaiCircuitBreaker = new CircuitBreaker({
  failureThreshold: 5,
  successThreshold: 2,
  timeout: 60000, // 1 minute
});

const response = await openaiCircuitBreaker.execute(() =>
  openaiAdapter.chat(messages)
);
```

-----

# **13. Testing Requirements**

## **13.1 Unit Tests**

```typescript
// packages/api/tests/services/aggregator.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AggregatorService } from '@/services/aggregator';

describe('AggregatorService', () => {
  let service: AggregatorService;
  let mockPrisma: any;
  
  beforeEach(() => {
    mockPrisma = {
      iteration: {
        findUniqueOrThrow: vi.fn(),
      },
      judgment: {
        findMany: vi.fn(),
      },
    };
    
    service = new AggregatorService(mockPrisma);
  });
  
  describe('calculateCompositeScores', () => {
    it('should calculate weighted average correctly', () => {
      const rubric: Rubric = [
        { name: 'Helpfulness', weight: 0.5, scale: { min: 0, max: 5 } },
        { name: 'Accuracy', weight: 0.5, scale: { min: 0, max: 5 } },
      ];
      
      const judgments = [
        { scores: { Helpfulness: 4, Accuracy: 5 } },
        { scores: { Helpfulness: 5, Accuracy: 4 } },
      ];
      
      const result = service.calculateCompositeScores(
        [{ id: '1', outputs: [{ judgments }] }],
        rubric
      );
      
      // (4+5)/2 * 0.5 + (5+4)/2 * 0.5 = 4.5
      expect(result['1']).toBe(4.5);
    });
    
    it('should handle missing scores gracefully', () => {
      const rubric: Rubric = [
        { name: 'Helpfulness', weight: 0.5, scale: { min: 0, max: 5 } },
        { name: 'Accuracy', weight: 0.5, scale: { min: 0, max: 5 } },
      ];
      
      const judgments = [
        { scores: { Helpfulness: 4 } }, // Missing Accuracy
      ];
      
      const result = service.calculateCompositeScores(
        [{ id: '1', outputs: [{ judgments }] }],
        rubric
      );
      
      // 4 * 0.5 + 0 * 0.5 = 2.0
      expect(result['1']).toBe(2.0);
    });
  });
  
  describe('bootstrapCI', () => {
    it('should calculate confidence intervals', () => {
      const rubric: Rubric = [
        { name: 'Helpfulness', weight: 1.0, scale: { min: 0, max: 5 } },
      ];
      
      const scores = Array(100).fill(0).map(() => ({ Helpfulness: 4 }));
      const judgments = scores.map(s => ({ scores: s, mode: 'POINTWISE' }));
      
      const result = service.bootstrapCI(
        [{ id: '1', outputs: [{ judgments }] }],
        rubric,
        1000
      );
      
      expect(result['1'].lower).toBeGreaterThan(3.5);
      expect(result['1'].upper).toBeLessThan(4.5);
    });
  });
});
```

## **13.2 Integration Tests**

```typescript
// packages/api/tests/integration/iteration.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { PrismaClient } from '@prisma/client';
import { IterationOrchestrator } from '@/services/orchestrator';

describe('Iteration E2E', () => {
  let prisma: PrismaClient;
  let orchestrator: IterationOrchestrator;
  let testProjectId: string;
  let testExperimentId: string;
  
  beforeAll(async () => {
    prisma = new PrismaClient();
    orchestrator = new IterationOrchestrator(prisma, /* queues */);
    
    // Create test data
    const project = await prisma.project.create({
      data: { name: 'Test Project', slug: 'test-project' },
    });
    testProjectId = project.id;
    
    const experiment = await prisma.experiment.create({
      data: {
        projectId: testProjectId,
        name: 'Test Experiment',
        goal: 'Test goal',
        rubric: [{ name: 'Quality', weight: 1.0, scale: { min: 0, max: 5 } }],
        stopRules: { maxIterations: 1, minDeltaThreshold: 0.01 },
      },
    });
    testExperimentId = experiment.id;
    
    // Add prompt version, model configs, judge configs, test cases
    // ...
  });
  
  afterAll(async () => {
    // Cleanup
    await prisma.experiment.deleteMany({ where: { projectId: testProjectId } });
    await prisma.project.delete({ where: { id: testProjectId } });
    await prisma.$disconnect();
  });
  
  it('should complete full iteration lifecycle', async () => {
    // Start iteration
    const iterationId = await orchestrator.startIteration(
      testExperimentId,
      /* promptVersionId */
    );
    
    expect(iterationId).toBeTruthy();
    
    // Wait for completion (with timeout)
    await waitForIterationComplete(iterationId, 60000);
    
    // Verify results
    const iteration = await prisma.iteration.findUnique({
      where: { id: iterationId },
      include: {
        modelRuns: true,
      },
    });
    
    expect(iteration?.status).toBe('COMPLETED');
    expect(iteration?.modelRuns.every(r => r.status === 'COMPLETED')).toBe(true);
    expect(iteration?.metrics).toBeTruthy();
  }, 120000); // 2 minute timeout
});

async function waitForIterationComplete(
  iterationId: string,
  timeoutMs: number
): Promise<void> {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeoutMs) {
    const iteration = await prisma.iteration.findUnique({
      where: { id: iterationId },
    });
    
    if (iteration?.status === 'COMPLETED' || iteration?.status === 'FAILED') {
      return;
    }
    
    await sleep(1000);
  }
  
  throw new Error('Iteration did not complete in time');
}
```

## **13.3 E2E Tests (Playwright)**

```typescript
// packages/web/tests/e2e/experiment-wizard.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Experiment Wizard', () => {
  test('should create experiment end-to-end', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'Test123!@#');
    await page.click('button[type="submit"]');
    
    // Navigate to create experiment
    await page.goto('/projects/test-project/experiments/new');
    
    // Step 1: Objective
    await expect(page.locator('h2')).toContainText('Objective');
    await page.fill('textarea[name="goal"]', 'Test objective with at least 20 characters to meet validation');
    await page.click('button:has-text("Continue")');
    
    // Step 2: Rubric
    await expect(page.locator('h2')).toContainText('Rubric');
    await page.click('button:has-text("Draft Rubric")');
    await page.waitForSelector('[data-testid="rubric-table"]');
    await page.click('button:has-text("Continue")');
    
    // Step 3: Prompt
    await expect(page.locator('h2')).toContainText('Seed Prompt');
    await page.fill('textarea[name="prompt"]', 'You are a helpful assistant. When the user asks {{question}}, respond clearly.');
    await page.click('button:has-text("Continue")');
    
    // Step 4: Dataset
    await expect(page.locator('h2')).toContainText('Test Data');
    await page.click('button:has-text("Generate with AI")');
    await page.fill('textarea[name="domainHints"]', 'customer support questions');
    await page.fill('input[name="count"]', '20');
    await page.click('button:has-text("Generate Synthetic Cases")');
    await page.waitForSelector('[data-testid="dataset-preview"]');
    await page.click('button:has-text("Continue")');
    
    // Step 5: Models
    await expect(page.locator('h2')).toContainText('Models');
    await page.check('input[value="gpt-4o"]');
    await page.check('input[value="gpt-4o-mini"]');
    await page.click('button:has-text("Continue")');
    
    // Step 6: Judges
    await expect(page.locator('h2')).toContainText('Judges');
    await page.check('input[value="gpt-4o"]');
    await page.click('button:has-text("Continue")');
    
    // Step 7: Stop Rules
    await expect(page.locator('h2')).toContainText('Stop Rules');
    await page.fill('input[name="maxIterations"]', '5');
    await page.fill('input[name="maxBudgetUsd"]', '10');
    await page.click('button:has-text("Create Experiment")');
    
    // Verify redirect to experiment page
    await expect(page).toHaveURL(/\/experiments\/[a-z0-9]+/);
    await expect(page.locator('h1')).toContainText('Test Experiment');
  });
});
```

## **13.4 Test Coverage Requirements**

|Component           |Target Coverage|Critical Paths              |
|--------------------|---------------|----------------------------|
|**Service Layer**   |90%+           |All business logic          |
|**API Routes**      |85%+           |All endpoints + error cases |
|**LLM Adapters**    |80%+           |Core functionality + retries|
|**Utilities**       |95%+           |All helper functions        |
|**React Components**|70%+           |Core interactions           |
|**E2E Flows**       |100%           |Happy paths for all features|

-----

# **14. Deployment Specifications**

## **14.1 Environment Variables**

```bash
# .env.example

# Database
DATABASE_URL="postgresql://edison:password@localhost:5432/edison"

# Redis
REDIS_URL="redis://localhost:6379"

# JWT
JWT_SECRET="your-secret-key-min-32-chars-long"

# Encryption (generate with crypto.generateKeyPair())
ENCRYPTION_PUBLIC_KEY="hex-encoded-public-key"
ENCRYPTION_PRIVATE_KEY="hex-encoded-private-key"

# LLM Providers (optional, can be added via UI)
OPENAI_API_KEY=""
ANTHROPIC_API_KEY=""

# Application
NODE_ENV="production"
PORT="8080"
NEXT_PUBLIC_API_URL="http://localhost:8080"

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
LOG_LEVEL="info"

# Email (optional)
SMTP_HOST=""
SMTP_PORT="587"
SMTP_USER=""
SMTP_PASS=""
SMTP_FROM="noreply@edison.local"
```

## **14.2 Docker Compose (Production)**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: edison
      POSTGRES_USER: edison
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U edison"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - edison-network
  
  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - edison-network
  
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: api
    restart: always
    environment:
      DATABASE_URL: postgresql://edison:${DB_PASSWORD}@db:5432/edison
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
      ENCRYPTION_PUBLIC_KEY: ${ENCRYPTION_PUBLIC_KEY}
      ENCRYPTION_PRIVATE_KEY: ${ENCRYPTION_PRIVATE_KEY}
      NODE_ENV: production
      PORT: 8080
    ports:
      - "8080:8080"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - edison-network
  
  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: worker
    restart: always
    environment:
      DATABASE_URL: postgresql://edison:${DB_PASSWORD}@db:5432/edison
      REDIS_URL: redis://redis:6379
      NODE_ENV: production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 3
    networks:
      - edison-network
  
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: web
    restart: always
    environment:
      NEXT_PUBLIC_API_URL: http://api:8080
    ports:
      - "3000:3000"
    depends_on:
      - api
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - edison-network
  
  # Optional: Backup service
  backup:
    image: postgres:16-alpine
    restart: on-failure
    environment:
      PGHOST: db
      PGUSER: edison
      PGPASSWORD: ${DB_PASSWORD}
      PGDATABASE: edison
    volumes:
      - ./backups:/backups
    entrypoint: |
      sh -c '
      while true; do
        TIMESTAMP=$$(date +%Y%m%d_%H%M%S)
        pg_dump > /backups/backup_$$TIMESTAMP.sql
        find /backups -name "backup_*.sql" -mtime +30 -delete
        sleep 86400
      done
      '
    depends_on:
      - db
    networks:
      - edison-network

volumes:
  postgres_data:
  redis_data:

networks:
  edison-network:
    driver: bridge
```

## **14.3 Health Checks**

```typescript
// packages/api/src/routes/health.ts
import { Router } from 'express';

const router = Router();

router.get('/health', async (req, res) => {
  const checks = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    services: {
      database: 'unknown',
      redis: 'unknown',
      workers: 'unknown',
    },
  };
  
  // Check database
  try {
    await prisma.$queryRaw`SELECT 1`;
    checks.services.database = 'healthy';
  } catch (error) {
    checks.services.database = 'unhealthy';
    checks.status = 'degraded';
  }
  
  // Check Redis
  try {
    await redis.ping();
    checks.services.redis = 'healthy';
  } catch (error) {
    checks.services.redis = 'unhealthy';
    checks.status = 'degraded';
  }
  
  // Check workers
  try {
    const queueInfo = await executeQueue.getJobCounts();
    checks.services.workers = queueInfo.active > 0 ? 'healthy' : 'idle';
  } catch (error) {
    checks.services.workers = 'unhealthy';
    checks.status = 'degraded';
  }
  
  const statusCode = checks.status === 'ok' ? 200 : 503;
  res.status(statusCode).json(checks);
});

router.get('/readiness', async (req, res) => {
  // Check if service is ready to accept traffic
  try {
    await prisma.$queryRaw`SELECT 1`;
    await redis.ping();
    res.status(200).json({ ready: true });
  } catch (error) {
    res.status(503).json({ ready: false, error: error.message });
  }
});

export default router;
```

## **14.4 Deployment Checklist**

**Pre-Deployment:**

- [ ] All tests passing (unit + integration + E2E)
- [ ] Database migrations reviewed and tested
- [ ] Environment variables configured
- [ ] Encryption keys generated and secured
- [ ] Dependencies audited (`npm audit`)
- [ ] Docker images built and tagged
- [ ] Backup strategy in place
- [ ] Rollback plan documented

**Deployment:**

- [ ] Pull latest code
- [ ] Run database migrations
- [ ] Build and push Docker images
- [ ] Update docker-compose.yml
- [ ] Start services with `docker-compose up -d`
- [ ] Verify health checks
- [ ] Run smoke tests

**Post-Deployment:**

- [ ] Monitor logs for errors
- [ ] Check metrics dashboard
- [ ] Test critical user flows
- [ ] Verify background jobs running
- [ ] Update documentation
- [ ] Notify team

-----

# **15. Accessibility Requirements (WCAG AA)**

## **15.1 Keyboard Navigation**

**Requirements:**

- All interactive elements reachable via Tab/Shift+Tab
- Visible focus indicators (2px outline, accent color)
- Logical tab order (follows visual flow)
- Skip links for main content
- Keyboard shortcuts documented (?, Ctrl+K for search)

**Implementation:**

```typescript
// Focus trap for modals
import { FocusTrap } from '@headlessui/react';

<FocusTrap>
  <Dialog>
    {/* Content */}
  </Dialog>
</FocusTrap>

// Skip link
<a href="#main-content" className="sr-only focus:not-sr-only">
  Skip to main content
</a>
```

## **15.2 Screen Reader Support**

**Requirements:**

- All images have alt text
- Form inputs have labels (visible or aria-label)
- Buttons have descriptive text or aria-label
- ARIA landmarks (main, nav, aside, footer)
- ARIA live regions for dynamic content
- Status messages announced

**Implementation:**

```tsx
// Progress updates
<div role="status" aria-live="polite" aria-atomic="true">
  {`Iteration ${number} is ${status}`}
</div>

// Loading states
<button aria-busy={isLoading} aria-label="Run iteration">
  {isLoading ? 'Running...' : 'Run'}
</button>

// Dynamic content
<div
  role="alert"
  aria-live="assertive"
  className={error ? 'block' : 'sr-only'}
>
  {error}
</div>
```

## **15.3 Color Contrast**

**Requirements:**

- Text contrast ratio ≥ 4.5:1 (normal text)
- Text contrast ratio ≥ 3:1 (large text 18pt+)
- UI component contrast ratio ≥ 3:1
- No color-only information (use icons + labels)

**Validated Combinations:**

```typescript
// WCAG AA compliant
const colors = {
  'text-on-white': '#0F172A',        // 15.5:1
  'text-muted-on-white': '#475569',  // 7.2:1
  'accent-on-white': '#0F766E',      // 4.8:1
  'error-on-white': '#DC2626',       // 5.9:1
  'success-on-white': '#16A34A',     // 4.6:1
};
```

## **15.4 Form Validation**

**Requirements:**

- Errors announced to screen readers
- Error messages linked to fields (aria-describedby)
- Required fields indicated (aria-required)
- Input constraints explained (maxlength, pattern)
- Success confirmation

**Implementation:**

```tsx
<div>
  <label htmlFor="email" className="required">
    Email
  </label>
  <input
    id="email"
    type="email"
    aria-required="true"
    aria-invalid={!!errors.email}
    aria-describedby={errors.email ? 'email-error' : undefined}
  />
  {errors.email && (
    <p id="email-error" className="error" role="alert">
      {errors.email.message}
    </p>
  )}
</div>
```

-----

# **16. Edge Cases & Corner Cases**

## **16.1 Empty States**

|Scenario             |Behavior                                          |
|---------------------|--------------------------------------------------|
|No projects          |Show welcome screen with “Create Project” CTA     |
|No experiments       |Show empty state with template suggestions        |
|No test cases        |Cannot run iteration; show upload/generate options|
|No prompt versions   |Wizard requires seed prompt before continuing     |
|No model configs     |Cannot run iteration; show “Add Model” button     |
|Zero budget          |Cannot run iteration; show budget increase prompt |
|All iterations failed|Show troubleshooting guide                        |
|No search results    |Show “No results found” with clear filters option |

## **16.2 Concurrent Operations**

|Scenario                                      |Behavior                                       |
|----------------------------------------------|-----------------------------------------------|
|Two users edit same prompt                    |Last write wins; show conflict warning         |
|Run iteration while another running           |Lock experiment; show “Already running” message|
|Delete project with active runs               |Prompt to cancel runs first                    |
|Pause iteration during aggregation            |Cannot pause; must wait for phase to complete  |
|Approve suggestion while new iteration running|Lock suggestion until iteration completes      |

## **16.3 Large Data Sets**

|Scenario            |Behavior                                     |
|--------------------|---------------------------------------------|
|10,000 test cases   |Batch process in chunks of 100; show progress|
|50+ iterations      |Paginate iteration list; lazy load charts    |
|100+ prompt versions|Show timeline with collapsible sections      |
|1,000+ judgments    |Aggregate on backend; show summary stats only|
|Large prompt (>20KB)|Warn about token limits; suggest splitting   |

## **16.4 Provider Failures**

|Scenario        |Behavior                                                         |
|----------------|-----------------------------------------------------------------|
|OpenAI API down |Retry 3x with backoff; mark run as failed; notify user           |
|Rate limit hit  |Queue jobs; wait and retry automatically                         |
|Invalid API key |Halt immediately; prompt user to update credentials              |
|Model deprecated|Show warning; suggest alternative model                          |
|Timeout (>60s)  |Cancel request; mark output as failed; continue with other models|

## **16.5 Malformed Inputs**

|Scenario                           |Behavior                                              |
|-----------------------------------|------------------------------------------------------|
|Prompt with no variables           |Valid; treat as static prompt                         |
|Test case missing required variable|Skip case; log warning; show in UI                    |
|Judge returns non-JSON             |Retry once; if fails, log error and use default scores|
|Rubric weights don’t sum to 1.0    |Auto-normalize on save                                |
|Negative budget                    |Validation error; min $0.01                           |
|Max iterations = 0                 |Validation error; min 1                               |

## **16.6 Network Issues**

|Scenario                |Behavior                                      |
|------------------------|----------------------------------------------|
|SSE connection drops    |Auto-reconnect every 5s; show “Reconnecting…” |
|WebSocket fails         |Fallback to polling every 3s                  |
|File upload interrupted |Resume from last chunk (if supported) or retry|
|API request times out   |Show error toast; offer retry button          |
|Database connection lost|Queue writes; retry when reconnected          |

-----

# **17. Migration & Upgrade Paths**

## **17.1 Database Migrations**

**Strategy:** Alembic (Python) or Prisma Migrate (TypeScript)

**Process:**

1. Create migration: `prisma migrate dev --name add_X_to_Y`
1. Review generated SQL
1. Test on staging database
1. Run in production: `prisma migrate deploy`
1. Verify no data loss

**Rollback Plan:**

- Keep last 10 migrations
- Manual rollback via SQL if needed
- Always backup before migration

**Example:**

```prisma
// Add new column with default
model Experiment {
  // ...
  maxConcurrentRuns Int @default(5)
}

// Migration will be:
ALTER TABLE experiments ADD COLUMN max_concurrent_runs INTEGER DEFAULT 5;
```

## **17.2 Breaking Changes**

**Semantic Versioning:**

- Major version (v2.0.0): Breaking changes
- Minor version (v1.1.0): New features, backward compatible
- Patch version (v1.0.1): Bug fixes

**Deprecation Process:**

1. Announce deprecation 2 versions ahead
1. Add deprecation warnings in UI/API
1. Provide migration guide
1. Remove in next major version

**Example:**

```typescript
// v1.5.0: Deprecate old API
/**
 * @deprecated Use experimentRouter.create() instead. Will be removed in v2.0.0.
 */
export const createExperiment = ...;

// v1.6.0: Show warnings
if (usingOldAPI) {
  logger.warn('Old API is deprecated. Migrate to new API.');
}

// v2.0.0: Remove
// Old API deleted
```

## **17.3 Data Migrations**

**Scenario:** Changing prompt structure (e.g., split into sections)

```typescript
// Migration script
async function migratePrompts() {
  const prompts = await prisma.promptVersion.findMany();
  
  for (const prompt of prompts) {
    // Parse old format
    const sections = parsePromptSections(prompt.text);
    
    // Update to new format
    await prisma.promptVersion.update({
      where: { id: prompt.id },
      data: {
        sections: sections,
        // Keep old text for rollback
        legacyText: prompt.text,
      },
    });
  }
  
  logger.info(`Migrated ${prompts.length} prompts`);
}
```

-----

# **18. Monitoring & Observability**

## **18.1 Metrics to Track**

**Application Metrics:**

- Request rate (req/sec)
- Response time (p50, p95, p99)
- Error rate (% of requests)
- Active users (concurrent sessions)
- Job queue depth (pending jobs)
- Job processing rate (jobs/min)

**Business Metrics:**

- Experiments created (per day)
- Iterations run (per day)
- Average cost per iteration
- Budget utilization (%)
- Prompt versions created (per experiment)
- Review approval rate (%)

**Infrastructure Metrics:**

- CPU usage (%)
- Memory usage (MB)
- Disk usage (GB)
- Database connections (active/idle)
- Redis memory (MB)
- Cache hit rate (%)

**LLM Metrics:**

- API calls (per provider)
- Token usage (prompt + completion)
- Cost (per provider, per model)
- Latency (ms)
- Error rate (per provider)
- Cache hit rate (%)

## **18.2 Alerting Rules**

**Critical (PagerDuty/SMS):**

```yaml
- name: database_down
  condition: db_healthy == false for 2m
  action: page_oncall
  
- name: api_error_rate_high
  condition: error_rate > 0.05 for 5m
  action: page_oncall
  
- name: queue_backing_up
  condition: job_queue_depth > 1000 for 10m
  action: page_oncall
  
- name: disk_full
  condition: disk_usage > 0.9
  action: page_oncall
```

**Warning (Email/Slack):**

```yaml
- name: budget_high
  condition: budget_utilization > 0.8
  action: email_admins
  
- name: slow_queries
  condition: query_p95 > 1000ms for 10m
  action: slack_channel
  
- name: high_latency
  condition: api_p95 > 2000ms for 5m
  action: slack_channel
```

## **18.3 Logging Best Practices**

**Structured Logging:**

```typescript
logger.info({
  action: 'iteration.started',
  experimentId: 'exp_123',
  iterationNumber: 3,
  userId: 'user_456',
  estimatedCost: 2.50,
  timestamp: new Date().toISOString(),
});
```

**Log Levels:**

- `DEBUG`: Detailed flow (dev only)
- `INFO`: Business events
- `WARN`: Recoverable errors, degraded state
- `ERROR`: Failures requiring investigation
- `FATAL`: System crash

**Never Log:**

- API keys or credentials
- Passwords
- Sensitive user data (PII)
- Full stack traces in production (log trace ID instead)

-----

# **19. Final Specifications Summary**

## **19.1 Completion Checklist**

**Core Features:**

- [x] User authentication & authorization
- [x] Project & experiment management
- [x] Multi-step wizard for experiment creation
- [x] AI-assisted input (Draft/Complete/Improve)
- [x] Multi-provider LLM integration
- [x] Dataset upload & generation (synthetic/adversarial)
- [x] Model execution across test cases
- [x] Ensemble judging (pointwise + pairwise)
- [x] Statistical aggregation (composite scores, CIs, rankings)
- [x] Diff-based prompt refinement
- [x] Human-in-the-loop review
- [x] Real-time progress updates (SSE)
- [x] Side-by-side output viewer
- [x] Cost tracking & budget enforcement
- [x] Stop rules & convergence detection
- [x] Prompt version history
- [x] Export functionality

**Non-Functional:**

- [x] Type-safe API (tRPC + Zod)
- [x] Secure credential storage (encryption)
- [x] Rate limiting & CSRF protection
- [x] Error handling & graceful degradation
- [x] Retry logic for LLM calls
- [x] Circuit breaker pattern
- [x] Comprehensive logging
- [x] Health checks
- [x] Docker deployment
- [x] Accessibility (WCAG AA)
- [x] Test coverage (unit/integration/E2E)

## **19.2 API Routes Summary**

```
POST   /api/trpc/auth.register
POST   /api/trpc/auth.login
GET    /api/trpc/auth.me
POST   /api/trpc/auth.logout

GET    /api/trpc/project.list
GET    /api/trpc/project.get
POST   /api/trpc/project.create
PATCH  /api/trpc/project.update
DELETE /api/trpc/project.delete

POST   /api/trpc/provider.create
GET    /api/trpc/provider.list
PATCH  /api/trpc/provider.update
DELETE /api/trpc/provider.delete

GET    /api/trpc/experiment.list
GET    /api/trpc/experiment.get
POST   /api/trpc/experiment.create
PATCH  /api/trpc/experiment.update
DELETE /api/trpc/experiment.delete

POST   /api/trpc/prompt.create
GET    /api/trpc/prompt.get
GET    /api/trpc/prompt.history
GET    /api/trpc/prompt.diff

POST   /api/trpc/dataset.upload
POST   /api/trpc/dataset.generate
GET    /api/trpc/dataset.list
DELETE /api/trpc/dataset.delete

POST   /api/trpc/model.add
GET    /api/trpc/model.list
DELETE /api/trpc/model.remove

POST   /api/trpc/judge.add
GET    /api/trpc/judge.list
DELETE /api/trpc/judge.remove

POST   /api/trpc/iteration.start
GET    /api/trpc/iteration.get
POST   /api/trpc/iteration.pause
POST   /api/trpc/iteration.resume
POST   /api/trpc/iteration.cancel

GET    /api/trpc/suggestion.list
POST   /api/trpc/review.approve
POST   /api/trpc/review.reject

POST   /api/trpc/aiAssist.draftObjective
POST   /api/trpc/aiAssist.draftRubric
POST   /api/trpc/aiAssist.draftPrompts
POST   /api/trpc/aiAssist.improvePrompt
POST   /api/trpc/aiAssist.generateSynthetic

POST   /api/trpc/export.bundle

GET    /api/iterations/:id/stream (SSE)
GET    /api/health
GET    /api/readiness
```

## **19.3 Technology Stack Summary**

```yaml
Backend:
  Runtime: Node.js 20+
  Framework: Hono
  Language: TypeScript 5.3+
  Database: PostgreSQL 16
  ORM: Prisma 5.11+
  Cache/Queue: Redis 7.2 + BullMQ
  Auth: JWT + bcrypt
  Validation: Zod

Frontend:
  Framework: Next.js 14 (App Router)
  UI: React 18 + TypeScript
  Styling: Tailwind CSS + shadcn/ui
  State: TanStack Query + Zustand
  API: tRPC
  Charts: Recharts
  Animation: Framer Motion

LLM:
  Providers: OpenAI, Anthropic, Google, AWS, Azure
  SDKs: Official provider SDKs
  Caching: Redis (content-addressed)

DevOps:
  Containers: Docker + Docker Compose
  CI/CD: GitHub Actions
  Monitoring: OpenTelemetry
  Testing: Vitest + Playwright
```

-----

# **20. Glossary**

|Term                   |Definition                                                    |
|-----------------------|--------------------------------------------------------------|
|**Composite Score**    |Weighted average of criterion scores across rubric            |
|**Convergence**        |When prompt improvements plateau (delta below threshold)      |
|**Diff**               |Unified diff showing additions/deletions to prompt text       |
|**Ensemble**           |Multiple judges evaluating same outputs for robustness        |
|**Facet**              |Categorization dimension (tags, length, difficulty)           |
|**HITL**               |Human-In-The-Loop: manual review before applying changes      |
|**Iteration**          |One complete cycle: execute → judge → aggregate → refine      |
|**Pairwise**           |Comparing two outputs side-by-side to determine winner        |
|**Pointwise**          |Scoring single output against rubric criteria                 |
|**Prompt Version**     |Immutable snapshot of prompt text + metadata                  |
|**Rubric**             |Set of evaluation criteria with weights and scales            |
|**Seed Prompt**        |Initial prompt that starts the optimization loop              |
|**Stop Rule**          |Condition that halts iteration loop (budget, convergence, etc)|
|**Synthetic Dataset**  |Test cases generated by AI for diversity                      |
|**Adversarial Dataset**|Test cases designed to expose weaknesses                      |

-----

