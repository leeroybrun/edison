You will implement a really advanced prompt engineering app that let us define the goal of the prompt, an example/base first prompt iteration (or have an LLM generate one for us), and then test the prompt ideally on multiple pre-defined test data (or have another LLM generate some test data to be able to test the prompts) by multiple LLMs, record the results, and then have multiple other LLM evaluate the results based on the goals, the prompt and the input data, and then give precise suggestions/ideas to refine the prompt. then we give all of this to another final LLM which evaluate everything together, the suggestions of the LLM judges, etc and refine the prompt to create a new iteration of the prompt. then from this new iteration, we can start the whole process again if we want to. and integrate all of this with some human-in-the-loop validation/summaries. we would have to integrate a lof of llm features and thinking processes to produce high-quality results like sequential thinking, chain-of-thoughts, etc.

The goal of our tool would be to be able to easily build prompts and have them refined by ai and human-in-the-loop in an iterative process and as quickly and as automated as possible, with the LLM doing most of the work (even for the first prompt, generating/complementing/refining test data, etc) so that building, testing and refining prompts can be as easy and fast as possible with a very very good quality in the end validated/refined by multiple LLMs and human validation.

# Edison v1 - Complete Build Specification

## **Your Role & Expertise**

You are an **Elite Full-Stack TypeScript Architect** with 10+ years building production AI applications. You’re known for:

- **Obsessive code quality**: Every file follows SOLID principles, DRY, clean architecture patterns
- **Type safety zealot**: Leveraging TypeScript’s type system to prevent runtime errors entirely
- **User experience perfectionist**: Building interfaces that feel magical and intuitive
- **Production mindset**: Writing code that scales, monitors itself, handles errors gracefully, and ships reliably
- **AI/LLM mastery**: Deep expertise in prompt engineering, multi-provider orchestration, structured outputs, streaming, and cost optimization

**Tech Stack Expertise:**

- **Backend**: Node.js 20+, Hono/tRPC, Prisma, Zod, BullMQ
- **Frontend**: Next.js 14 App Router, React 18, TypeScript 5.3+, TanStack Query, Zustand
- **UI**: Tailwind CSS, shadcn/ui, Framer Motion, Radix UI primitives
- **AI**: Vercel AI SDK, OpenAI SDK, Anthropic SDK, streaming & structured outputs
- **Data**: PostgreSQL, Prisma migrations, complex queries with CTEs
- **Real-time**: Server-Sent Events, optimistic updates, WebSocket fallback
- **Testing**: Vitest, Playwright, MSW for API mocking
- **DevOps**: Docker Compose, Railway/Render deployment, OpenTelemetry observability

**Constraints & Principles:**

- ✅ Type-safe end-to-end (shared Zod schemas between frontend/backend)
- ✅ Zero runtime errors (validate everything at boundaries)
- ✅ Graceful degradation (offline-first where possible, skeleton loaders)
- ✅ Accessible (WCAG AA, keyboard nav, screen reader tested)
- ✅ Fast (Server Components, streaming, optimistic updates, < 1s perceived latency)
- ✅ Observable (structured logging, tracing, metrics, error tracking)
- ✅ Testable (pure functions, dependency injection, comprehensive test coverage)
- ❌ No premature abstraction (build features first, extract patterns second)
- ❌ No magic strings (use const enums and branded types)
- ❌ No any types (use unknown and narrow with guards)

-----

## **1. Product Vision**

**Edison** is the world’s most advanced prompt engineering workbench. It combines:

- **Human creativity** (empty inputs, clear intent)
- **AI acceleration** (Draft/Complete/Improve on every field)
- **Scientific rigor** (multi-model evaluation, statistical significance, coverage-driven testing)
- **Transparent iteration** (diff-based refinement, version history, audit trails)

**Core differentiators:**

1. **Human-first inputs with AI-assist**: Not a black box optimizer. Humans lead, AI accelerates.
1. **Diff-based prompt refinement**: See exactly what changed and why, like Git for prompts.
1. **Ensemble evaluation**: Multiple judges, pairwise ranking, statistical confidence intervals.
1. **Coverage-guided testing**: Automatically find gaps in test distribution and generate adversarial cases.
1. **Cost-aware optimization**: Real-time budget tracking, early stopping, adaptive sampling.
1. **Local-first**: Self-hosted, single-tenant, no data leaves your infrastructure.

**User personas:**

- **AI Engineer**: Building production prompts, needs reliable testing and version control
- **Product Manager**: Wants to improve chatbot responses, needs easy iteration and metrics
- **ML Researcher**: Testing prompt techniques, needs statistical rigor and reproducibility
- **Startup Founder**: Bootstrapping AI features, needs quick wins with budget control

-----

## **2. High-Level Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                         Next.js 14 Frontend                      │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐              │
│  │  Wizards   │  │   Viewers    │  │  HITL UI   │              │
│  │ (RSC+RCC)  │  │ (Streaming)  │  │ (Review)   │              │
│  └────────────┘  └──────────────┘  └────────────┘              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ tRPC/SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                    Hono API Server (Node.js)                     │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐     │
│  │   tRPC    │  │    SSE    │  │  Webhook │  │   Auth   │     │
│  │  Router   │  │  Events   │  │ Handlers │  │  (JWT)   │     │
│  └───────────┘  └───────────┘  └──────────┘  └──────────┘     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Service Layer (Pure TS)                     │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Orchestrator   │  │  LLM Adapter │  │  Evaluator   │      │
│  │  (Iterations)   │  │  (Multi-⚡)   │  │  (Judges)    │      │
│  └─────────────────┘  └──────────────┘  └──────────────┘      │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Refiner       │  │  Generator   │  │  Aggregator  │      │
│  │  (Diff Engine)  │  │  (Datasets)  │  │  (Stats)     │      │
│  └─────────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    BullMQ Job Queue (Redis)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │  Execute    │ │   Judge     │ │  Refine     │              │
│  │  Runs       │ │   Outputs   │ │  Prompt     │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    PostgreSQL 16 + Prisma                        │
│  Projects • Experiments • Datasets • Runs • Judgments • etc.    │
└──────────────────────────────────────────────────────────────────┘
```

**Design Decisions:**

1. **tRPC over REST**: Type-safe RPC, shared types, no codegen needed
1. **BullMQ over Postgres queue**: Purpose-built job queue, Redis is negligible cost
1. **Server-Sent Events over WebSockets**: Simpler, auto-reconnects, HTTP/2 multiplexing
1. **Server Components + Client Islands**: Fast page loads, minimal JS, hydration where needed
1. **Prisma over raw SQL**: Type-safe queries, migrations, great DX
1. **Monorepo structure**: Shared types, easier refactoring, single deploy

-----

## **3. Data Model (Prisma Schema)**

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// ============================================================================
// CORE ENTITIES
// ============================================================================

model User {
  id            String    @id @default(cuid())
  email         String    @unique
  name          String?
  passwordHash  String
  role          UserRole  @default(EDITOR)
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  
  projects      ProjectMember[]
  reviews       Review[]
  
  @@map("users")
}

enum UserRole {
  VIEWER
  REVIEWER
  EDITOR
  ADMIN
  OWNER
}

model Project {
  id          String   @id @default(cuid())
  slug        String   @unique
  name        String
  description String?
  settings    Json     @default("{}")
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  
  members      ProjectMember[]
  providers    ProviderCredential[]
  experiments  Experiment[]
  datasets     Dataset[]
  
  @@map("projects")
}

model ProjectMember {
  id        String      @id @default(cuid())
  projectId String
  userId    String
  role      UserRole
  createdAt DateTime    @default(now())
  
  project   Project @relation(fields: [projectId], references: [id], onDelete: Cascade)
  user      User    @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  @@unique([projectId, userId])
  @@map("project_members")
}

model ProviderCredential {
  id              String   @id @default(cuid())
  projectId       String
  provider        LLMProvider
  label           String
  encryptedApiKey String   // Encrypted with libsodium
  config          Json     @default("{}")
  isActive        Boolean  @default(true)
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  
  project Project @relation(fields: [projectId], references: [id], onDelete: Cascade)
  
  @@unique([projectId, provider, label])
  @@map("provider_credentials")
}

enum LLMProvider {
  OPENAI
  ANTHROPIC
  GOOGLE_VERTEX
  AWS_BEDROCK
  AZURE_OPENAI
  OLLAMA
  OPENAI_COMPATIBLE
}

// ============================================================================
// EXPERIMENTS
// ============================================================================

model Experiment {
  id              String          @id @default(cuid())
  projectId       String
  name            String
  description     String?
  goal            String          // What we're trying to achieve
  rubric          Json            // Array of {criterion, description, weight, scale}
  safetyConfig    Json            @default("{}") // PII, moderation, jailbreak rules
  selectorConfig  Json            @default("{}") // How to pick best prompts
  refinerConfig   Json            @default("{}") // Diff generation rules
  stopRules       Json            @default("{}") // Max iterations, delta threshold, budget
  status          ExperimentStatus @default(DRAFT)
  createdAt       DateTime        @default(now())
  updatedAt       DateTime        @updatedAt
  
  project         Project          @relation(fields: [projectId], references: [id], onDelete: Cascade)
  promptVersions  PromptVersion[]
  iterations      Iteration[]
  modelConfigs    ModelConfig[]
  judgeConfigs    JudgeConfig[]
  
  @@index([projectId, status])
  @@map("experiments")
}

enum ExperimentStatus {
  DRAFT
  RUNNING
  PAUSED
  COMPLETED
  ARCHIVED
}

model PromptVersion {
  id            String    @id @default(cuid())
  experimentId  String
  version       Int       // Auto-incrementing version number
  parentId      String?   // Previous version
  text          String    @db.Text
  systemText    String?   @db.Text
  fewShots      Json?     // Array of {user, assistant} examples
  toolsSchema   Json?     // For function calling
  changelog     String?   @db.Text // What changed in this version
  metadata      Json      @default("{}")
  isProduction  Boolean   @default(false)
  createdBy     String?   // User who created/approved this
  createdAt     DateTime  @default(now())
  
  experiment    Experiment      @relation(fields: [experimentId], references: [id], onDelete: Cascade)
  parent        PromptVersion?  @relation("VersionHistory", fields: [parentId], references: [id])
  children      PromptVersion[] @relation("VersionHistory")
  modelRuns     ModelRun[]
  suggestions   Suggestion[]
  iterations    Iteration[]
  
  @@unique([experimentId, version])
  @@index([experimentId, isProduction])
  @@map("prompt_versions")
}

model ModelConfig {
  id            String   @id @default(cuid())
  experimentId  String
  provider      LLMProvider
  modelId       String   // e.g., "gpt-4o", "claude-sonnet-4"
  params        Json     // {temperature, max_tokens, top_p, etc}
  seed          Int?     // For deterministic outputs
  isActive      Boolean  @default(true)
  
  experiment    Experiment @relation(fields: [experimentId], references: [id], onDelete: Cascade)
  modelRuns     ModelRun[]
  
  @@unique([experimentId, provider, modelId, params])
  @@map("model_configs")
}

model JudgeConfig {
  id            String      @id @default(cuid())
  experimentId  String
  provider      LLMProvider
  modelId       String
  mode          JudgeMode   // POINTWISE or PAIRWISE
  systemPrompt  String      @db.Text
  isActive      Boolean     @default(true)
  
  experiment    Experiment  @relation(fields: [experimentId], references: [id], onDelete: Cascade)
  judgments     Judgment[]
  
  @@map("judge_configs")
}

enum JudgeMode {
  POINTWISE
  PAIRWISE
}

// ============================================================================
// DATASETS
// ============================================================================

model Dataset {
  id          String      @id @default(cuid())
  projectId   String
  name        String
  kind        DatasetKind
  description String?
  metadata    Json        @default("{}")
  createdAt   DateTime    @default(now())
  updatedAt   DateTime    @updatedAt
  
  project     Project @relation(fields: [projectId], references: [id], onDelete: Cascade)
  cases       Case[]
  
  @@index([projectId, kind])
  @@map("datasets")
}

enum DatasetKind {
  GOLDEN       // Human-curated test cases
  SYNTHETIC    // LLM-generated diverse examples
  ADVERSARIAL  // Coverage-guided counterexamples
}

model Case {
  id          String   @id @default(cuid())
  datasetId   String
  input       Json     // The prompt variables/context
  expected    Json?    // Optional expected output for comparison
  tags        String[] // For filtering/grouping
  difficulty  Int?     @default(3) // 1-5 scale
  metadata    Json     @default("{}")
  createdAt   DateTime @default(now())
  
  dataset     Dataset  @relation(fields: [datasetId], references: [id], onDelete: Cascade)
  outputs     Output[]
  
  @@index([datasetId, tags])
  @@map("cases")
}

// ============================================================================
// RUNS & OUTPUTS
// ============================================================================

model Iteration {
  id                String    @id @default(cuid())
  experimentId      String
  number            Int       // 1, 2, 3...
  promptVersionId   String
  status            IterationStatus @default(PENDING)
  metrics           Json      @default("{}") // Aggregated scores, CIs, rankings
  totalCost         Float     @default(0)
  totalTokens       Int       @default(0)
  startedAt         DateTime?
  finishedAt        DateTime?
  
  experiment        Experiment    @relation(fields: [experimentId], references: [id], onDelete: Cascade)
  promptVersion     PromptVersion @relation(fields: [promptVersionId], references: [id])
  modelRuns         ModelRun[]
  
  @@unique([experimentId, number])
  @@index([experimentId, status])
  @@map("iterations")
}

enum IterationStatus {
  PENDING
  EXECUTING
  JUDGING
  AGGREGATING
  REFINING
  REVIEWING
  COMPLETED
  FAILED
}

model ModelRun {
  id                String    @id @default(cuid())
  iterationId       String
  promptVersionId   String
  modelConfigId     String
  datasetId         String    // Which dataset was used
  status            RunStatus @default(PENDING)
  tokensIn          Int       @default(0)
  tokensOut         Int       @default(0)
  costUsd           Float     @default(0)
  latencyMs         Int?
  startedAt         DateTime?
  finishedAt        DateTime?
  errorMessage      String?
  
  iteration         Iteration     @relation(fields: [iterationId], references: [id], onDelete: Cascade)
  promptVersion     PromptVersion @relation(fields: [promptVersionId], references: [id])
  modelConfig       ModelConfig   @relation(fields: [modelConfigId], references: [id])
  outputs           Output[]
  
  @@index([iterationId, status])
  @@index([promptVersionId, modelConfigId])
  @@map("model_runs")
}

enum RunStatus {
  PENDING
  RUNNING
  COMPLETED
  FAILED
  CANCELLED
}

model Output {
  id          String   @id @default(cuid())
  modelRunId  String
  caseId      String
  rawText     String   @db.Text
  parsed      Json?    // Structured output if applicable
  tokensOut   Int
  latencyMs   Int
  cached      Boolean  @default(false)
  metadata    Json     @default("{}")
  createdAt   DateTime @default(now())
  
  modelRun    ModelRun   @relation(fields: [modelRunId], references: [id], onDelete: Cascade)
  case        Case       @relation(fields: [caseId], references: [id])
  judgments   Judgment[]
  reviews     Review[]
  
  @@unique([modelRunId, caseId])
  @@index([modelRunId])
  @@map("outputs")
}

// ============================================================================
// EVALUATION
// ============================================================================

model Judgment {
  id              String    @id @default(cuid())
  outputId        String
  judgeConfigId   String
  mode            JudgeMode
  scores          Json      // {criterion: number} for pointwise
  rationales      Json      // {criterion: "brief explanation"}
  safetyFlags     Json      @default("{}")
  winnerOutputId  String?   // For pairwise
  metadata        Json      @default("{}")
  createdAt       DateTime  @default(now())
  
  output          Output      @relation(fields: [outputId], references: [id], onDelete: Cascade)
  judgeConfig     JudgeConfig @relation(fields: [judgeConfigId], references: [id])
  winnerOutput    Output?     @relation("PairwiseWinner", fields: [winnerOutputId], references: [id])
  
  @@index([outputId, judgeConfigId])
  @@map("judgments")
}

model Suggestion {
  id                String     @id @default(cuid())
  promptVersionId   String
  source            String     // "refiner_llm", "manual", etc
  diffUnified       String     @db.Text // Git-style unified diff
  note              String     @db.Text // Explanation of changes
  targetCriteria    String[]   // Which criteria this addresses
  status            SuggestionStatus @default(PENDING)
  createdAt         DateTime   @default(now())
  
  promptVersion     PromptVersion @relation(fields: [promptVersionId], references: [id], onDelete: Cascade)
  reviews           Review[]
  
  @@index([promptVersionId, status])
  @@map("suggestions")
}

enum SuggestionStatus {
  PENDING
  APPROVED
  REJECTED
  APPLIED
}

model Review {
  id            String   @id @default(cuid())
  suggestionId  String?  // If reviewing a suggestion
  outputId      String?  // If reviewing an output
  reviewerId    String
  decision      ReviewDecision
  notes         String?  @db.Text
  createdAt     DateTime @default(now())
  
  suggestion    Suggestion? @relation(fields: [suggestionId], references: [id], onDelete: Cascade)
  output        Output?     @relation(fields: [outputId], references: [id], onDelete: Cascade)
  reviewer      User        @relation(fields: [reviewerId], references: [id])
  
  @@index([suggestionId, reviewerId])
  @@map("reviews")
}

enum ReviewDecision {
  APPROVE
  REJECT
  REQUEST_CHANGES
}

// ============================================================================
// JOB QUEUE (for BullMQ tracking)
// ============================================================================

model Job {
  id            String      @id @default(cuid())
  type          JobType
  payload       Json
  status        JobStatus   @default(PENDING)
  priority      Int         @default(0)
  attempts      Int         @default(0)
  maxAttempts   Int         @default(3)
  lastError     String?     @db.Text
  workerId      String?
  scheduledAt   DateTime    @default(now())
  startedAt     DateTime?
  finishedAt    DateTime?
  
  @@index([status, scheduledAt, priority])
  @@map("jobs")
}

enum JobType {
  EXECUTE_RUN
  JUDGE_OUTPUTS
  AGGREGATE_SCORES
  REFINE_PROMPT
  GENERATE_DATASET
  SAFETY_SCAN
  EXPORT_BUNDLE
}

enum JobStatus {
  PENDING
  ACTIVE
  COMPLETED
  FAILED
  CANCELLED
}

// ============================================================================
// AUDIT & ANALYTICS
// ============================================================================

model AuditLog {
  id          String   @id @default(cuid())
  userId      String?
  action      String   // "prompt.created", "run.executed", etc
  entityType  String
  entityId    String
  changes     Json?
  metadata    Json     @default("{}")
  createdAt   DateTime @default(now())
  
  @@index([entityType, entityId])
  @@index([userId, createdAt])
  @@map("audit_logs")
}

model CostTracking {
  id          String   @id @default(cuid())
  projectId   String
  provider    LLMProvider
  modelId     String
  tokensIn    Int
  tokensOut   Int
  costUsd     Float
  timestamp   DateTime @default(now())
  metadata    Json     @default("{}")
  
  @@index([projectId, timestamp])
  @@index([provider, modelId, timestamp])
  @@map("cost_tracking")
}
```

-----

## **4. Shared Types & Validation (Zod Schemas)**

Create `packages/shared/src/schemas/` with all validation schemas:

```typescript
// packages/shared/src/schemas/rubric.ts
import { z } from 'zod';

export const RubricCriterionSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().min(1).max(500),
  weight: z.number().min(0).max(1),
  scale: z.object({
    min: z.number(),
    max: z.number(),
    labels: z.record(z.string()).optional(), // {0: "Poor", 5: "Excellent"}
  }),
});

export const RubricSchema = z.array(RubricCriterionSchema).min(1).refine(
  (criteria) => {
    const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0);
    return Math.abs(totalWeight - 1.0) < 0.01;
  },
  { message: 'Weights must sum to 1.0' }
);

export type RubricCriterion = z.infer<typeof RubricCriterionSchema>;
export type Rubric = z.infer<typeof RubricSchema>;

// packages/shared/src/schemas/experiment.ts
export const StopRulesSchema = z.object({
  maxIterations: z.number().int().min(1).max(100).default(10),
  minDeltaThreshold: z.number().min(0).max(1).default(0.02), // Stop if improvement < 2%
  maxBudgetUsd: z.number().min(0).optional(),
  maxTotalTokens: z.number().int().min(0).optional(),
  convergenceWindow: z.number().int().min(2).default(3), // Stop if no improvement for N iterations
});

export const ModelParamsSchema = z.object({
  temperature: z.number().min(0).max(2).default(1.0),
  maxTokens: z.number().int().min(1).max(100000).optional(),
  topP: z.number().min(0).max(1).optional(),
  topK: z.number().int().min(0).optional(),
  frequencyPenalty: z.number().min(-2).max(2).optional(),
  presencePenalty: z.number().min(-2).max(2).optional(),
  stop: z.array(z.string()).optional(),
});

// packages/shared/src/schemas/judgment.ts
export const PointwiseScoresSchema = z.record(z.number().min(0).max(5));
export const RationalesSchema = z.record(z.string().max(500));

export const JudgmentResultSchema = z.object({
  scores: PointwiseScoresSchema,
  rationales: RationalesSchema,
  safetyFlags: z.object({
    policyViolation: z.boolean(),
    piiDetected: z.boolean(),
    toxicContent: z.boolean(),
    jailbreakAttempt: z.boolean(),
  }),
});

// Export all schemas
export * from './rubric';
export * from './experiment';
export * from './judgment';
export * from './dataset';
export * from './prompt';
```

**Key principle**: Every API input/output goes through Zod validation. Types are derived from schemas, never written manually.

-----

## **5. LLM Adapter System**

```typescript
// packages/api/src/llm/types.ts
import { z } from 'zod';

export const LLMMessageSchema = z.object({
  role: z.enum(['system', 'user', 'assistant', 'function']),
  content: z.string(),
  name: z.string().optional(),
  functionCall: z.any().optional(),
});

export const LLMResponseSchema = z.object({
  text: z.string(),
  usage: z.object({
    promptTokens: z.number().int(),
    completionTokens: z.number().int(),
    totalTokens: z.number().int(),
  }),
  latencyMs: z.number().int(),
  cached: z.boolean(),
  model: z.string(),
  finishReason: z.enum(['stop', 'length', 'content_filter', 'tool_calls']),
  raw: z.any(), // Provider-specific response
});

export type LLMMessage = z.infer<typeof LLMMessageSchema>;
export type LLMResponse = z.infer<typeof LLMResponseSchema>;

export interface LLMAdapter {
  readonly provider: LLMProvider;
  readonly modelId: string;
  
  chat(
    messages: LLMMessage[],
    options?: {
      tools?: any[];
      params?: ModelParams;
      seed?: number;
      stream?: boolean;
    }
  ): Promise<LLMResponse>;
  
  streamChat(
    messages: LLMMessage[],
    options?: {
      tools?: any[];
      params?: ModelParams;
      seed?: number;
    }
  ): AsyncIterable<LLMStreamChunk>;
  
  estimateCost(promptTokens: number, completionTokens: number): number;
}

// packages/api/src/llm/adapters/openai.ts
import OpenAI from 'openai';
import { LLMAdapter, LLMResponse } from '../types';
import { createHash } from 'crypto';
import { redis } from '@/lib/redis';

export class OpenAIAdapter implements LLMAdapter {
  private client: OpenAI;
  
  constructor(
    private apiKey: string,
    public readonly provider: LLMProvider,
    public readonly modelId: string
  ) {
    this.client = new OpenAI({ apiKey });
  }
  
  async chat(messages, options = {}): Promise<LLMResponse> {
    const cacheKey = this.getCacheKey(messages, options);
    
    // Check cache
    const cached = await redis.get(cacheKey);
    if (cached) {
      return { ...JSON.parse(cached), cached: true };
    }
    
    const startTime = Date.now();
    
    const response = await this.client.chat.completions.create({
      model: this.modelId,
      messages: messages as any,
      temperature: options.params?.temperature,
      max_tokens: options.params?.maxTokens,
      top_p: options.params?.topP,
      frequency_penalty: options.params?.frequencyPenalty,
      presence_penalty: options.params?.presencePenalty,
      seed: options.seed,
      tools: options.tools,
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
      finishReason: response.choices[0].finish_reason as any,
      raw: response,
    };
    
    // Cache for 1 hour
    await redis.setex(cacheKey, 3600, JSON.stringify(result));
    
    return result;
  }
  
  private getCacheKey(messages: any[], options: any): string {
    const payload = JSON.stringify({
      provider: this.provider,
      model: this.modelId,
      messages,
      params: options.params,
      seed: options.seed,
    });
    return `llm:cache:${createHash('sha256').update(payload).digest('hex')}`;
  }
  
  estimateCost(promptTokens: number, completionTokens: number): number {
    // Pricing as of 2024 - update regularly
    const pricing: Record<string, { input: number; output: number }> = {
      'gpt-4o': { input: 0.0025, output: 0.01 },
      'gpt-4o-mini': { input: 0.00015, output: 0.0006 },
      'gpt-4-turbo': { input: 0.01, output: 0.03 },
    };
    
    const rates = pricing[this.modelId] || { input: 0.001, output: 0.002 };
    return (promptTokens * rates.input + completionTokens * rates.output) / 1000;
  }
}

// Create similar adapters for Anthropic, Vertex, etc.
// packages/api/src/llm/adapters/anthropic.ts
// packages/api/src/llm/adapters/vertex.ts
```

**Adapter Factory:**

```typescript
// packages/api/src/llm/factory.ts
import { ProviderCredential } from '@prisma/client';
import { LLMAdapter } from './types';
import { OpenAIAdapter } from './adapters/openai';
import { AnthropicAdapter } from './adapters/anthropic';
import { decrypt } from '@/lib/crypto';

export class LLMAdapterFactory {
  private cache = new Map<string, LLMAdapter>();
  
  async getAdapter(
    credential: ProviderCredential,
    modelId: string
  ): Promise<LLMAdapter> {
    const cacheKey = `${credential.id}:${modelId}`;
    
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)!;
    }
    
    const apiKey = await decrypt(credential.encryptedApiKey);
    
    let adapter: LLMAdapter;
    
    switch (credential.provider) {
      case 'OPENAI':
        adapter = new OpenAIAdapter(apiKey, credential.provider, modelId);
        break;
      case 'ANTHROPIC':
        adapter = new AnthropicAdapter(apiKey, credential.provider, modelId);
        break;
      // ... other providers
      default:
        throw new Error(`Unsupported provider: ${credential.provider}`);
    }
    
    this.cache.set(cacheKey, adapter);
    return adapter;
  }
}
```

-----

## **6. Core Services**

### **6.1 Orchestrator Service**

```typescript
// packages/api/src/services/orchestrator.ts
import { PrismaClient } from '@prisma/client';
import { Queue } from 'bullmq';
import { EventEmitter } from 'events';

export class IterationOrchestrator extends EventEmitter {
  constructor(
    private prisma: PrismaClient,
    private executeQueue: Queue,
    private judgeQueue: Queue,
    private refineQueue: Queue
  ) {
    super();
  }
  
  async startIteration(experimentId: string, promptVersionId: string): Promise<string> {
    // 1. Create iteration record
    const experiment = await this.prisma.experiment.findUniqueOrThrow({
      where: { id: experimentId },
      include: {
        modelConfigs: { where: { isActive: true } },
        judgeConfigs: { where: { isActive: true } },
      },
    });
    
    const lastIteration = await this.prisma.iteration.findFirst({
      where: { experimentId },
      orderBy: { number: 'desc' },
    });
    
    const iteration = await this.prisma.iteration.create({
      data: {
        experimentId,
        promptVersionId,
        number: (lastIteration?.number || 0) + 1,
        status: 'PENDING',
      },
    });
    
    this.emit('iteration:started', { iterationId: iteration.id });
    
    // 2. Get all datasets for this experiment
    const datasets = await this.prisma.dataset.findMany({
      where: { projectId: experiment.projectId },
      include: { cases: true },
    });
    
    // 3. Create ModelRuns for each model config
    const modelRuns = await Promise.all(
      experiment.modelConfigs.map(async (config) => {
        return this.prisma.modelRun.create({
          data: {
            iterationId: iteration.id,
            promptVersionId,
            modelConfigId: config.id,
            datasetId: datasets[0].id, // Use first dataset for now
            status: 'PENDING',
          },
        });
      })
    );
    
    // 4. Queue execution jobs
    await Promise.all(
      modelRuns.map((run) =>
        this.executeQueue.add('execute-run', {
          modelRunId: run.id,
          iterationId: iteration.id,
        })
      )
    );
    
    // Update iteration status
    await this.prisma.iteration.update({
      where: { id: iteration.id },
      data: { status: 'EXECUTING', startedAt: new Date() },
    });
    
    return iteration.id;
  }
  
  async onExecutionComplete(iterationId: string): Promise<void> {
    // Check if all runs are complete
    const runs = await this.prisma.modelRun.findMany({
      where: { iterationId },
      include: { outputs: true },
    });
    
    const allComplete = runs.every((r) => r.status === 'COMPLETED');
    if (!allComplete) return;
    
    this.emit('iteration:executed', { iterationId });
    
    // Update status and queue judging
    await this.prisma.iteration.update({
      where: { id: iterationId },
      data: { status: 'JUDGING' },
    });
    
    // Queue judging jobs
    const allOutputs = runs.flatMap((r) => r.outputs);
    await this.judgeQueue.add('judge-outputs', {
      iterationId,
      outputIds: allOutputs.map((o) => o.id),
    });
  }
  
  async onJudgingComplete(iterationId: string): Promise<void> {
    this.emit('iteration:judged', { iterationId });
    
    await this.prisma.iteration.update({
      where: { id: iterationId },
      data: { status: 'AGGREGATING' },
    });
    
    // Aggregate scores
    const metrics = await this.aggregateScores(iterationId);
    
    await this.prisma.iteration.update({
      where: { id: iterationId },
      data: {
        status: 'REFINING',
        metrics,
      },
    });
    
    this.emit('iteration:aggregated', { iterationId, metrics });
    
    // Check stop rules
    const shouldStop = await this.checkStopRules(iterationId);
    
    if (shouldStop) {
      await this.prisma.iteration.update({
        where: { id: iterationId },
        data: { status: 'COMPLETED', finishedAt: new Date() },
      });
      this.emit('iteration:completed', { iterationId });
      return;
    }
    
    // Queue refinement
    await this.refineQueue.add('refine-prompt', { iterationId });
  }
  
  private async aggregateScores(iterationId: string): Promise<any> {
    // Implementation in next section
  }
  
  private async checkStopRules(iterationId: string): Promise<boolean> {
    // Implementation in next section
  }
}
```

### **6.2 Evaluator Service**

```typescript
// packages/api/src/services/evaluator.ts
import { PrismaClient, JudgeConfig, Output } from '@prisma/client';
import { LLMAdapterFactory } from '@/llm/factory';
import { JudgmentResultSchema } from '@packages/shared';

export class EvaluatorService {
  constructor(
    private prisma: PrismaClient,
    private adapterFactory: LLMAdapterFactory
  ) {}
  
  async judgeOutputs(
    outputIds: string[],
    judgeConfigs: JudgeConfig[]
  ): Promise<void> {
    const outputs = await this.prisma.output.findMany({
      where: { id: { in: outputIds } },
      include: {
        case: true,
        modelRun: {
          include: {
            iteration: {
              include: {
                experiment: true,
              },
            },
          },
        },
      },
    });
    
    // Pointwise judging
    const pointwiseJudges = judgeConfigs.filter((j) => j.mode === 'POINTWISE');
    
    await Promise.all(
      outputs.flatMap((output) =>
        pointwiseJudges.map((judge) =>
          this.judgePointwise(output, judge)
        )
      )
    );
    
    // Pairwise judging (compare all pairs)
    const pairwiseJudges = judgeConfigs.filter((j) => j.mode === 'PAIRWISE');
    
    if (pairwiseJudges.length > 0) {
      await this.judgePairwise(outputs, pairwiseJudges);
    }
  }
  
  private async judgePointwise(
    output: Output & { case: Case; modelRun: any },
    judge: JudgeConfig
  ): Promise<void> {
    const experiment = output.modelRun.iteration.experiment;
    const rubric = experiment.rubric as Rubric;
    
    const credential = await this.prisma.providerCredential.findFirstOrThrow({
      where: {
        projectId: experiment.projectId,
        provider: judge.provider,
        isActive: true,
      },
    });
    
    const adapter = await this.adapterFactory.getAdapter(
      credential,
      judge.modelId
    );
    
    const prompt = this.buildPointwisePrompt(
      experiment.goal,
      rubric,
      output.case.input,
      output.rawText
    );
    
    const response = await adapter.chat([
      { role: 'system', content: judge.systemPrompt },
      { role: 'user', content: prompt },
    ], {
      params: { temperature: 0.3 }, // Low temp for consistency
      seed: 42,
    });
    
    // Parse structured output
    const result = JudgmentResultSchema.parse(JSON.parse(response.text));
    
    await this.prisma.judgment.create({
      data: {
        outputId: output.id,
        judgeConfigId: judge.id,
        mode: 'POINTWISE',
        scores: result.scores,
        rationales: result.rationales,
        safetyFlags: result.safetyFlags,
      },
    });
  }
  
  private buildPointwisePrompt(
    goal: string,
    rubric: Rubric,
    input: any,
    output: string
  ): string {
    return `# Evaluation Task

## Goal
${goal}

## Rubric
${JSON.stringify(rubric, null, 2)}

## Input
${JSON.stringify(input, null, 2)}

## Output to Evaluate
${output}

## Instructions
Evaluate the output against each criterion in the rubric. Return ONLY valid JSON with this structure:

{
  "scores": {
    "<criterion_name>": <number 0-5>
  },
  "rationales": {
    "<criterion_name>": "<1-2 sentence explanation>"
  },
  "safetyFlags": {
    "policyViolation": <boolean>,
    "piiDetected": <boolean>,
    "toxicContent": <boolean>,
    "jailbreakAttempt": <boolean>
  }
}

Be strict and objective. No chain-of-thought, just scores and brief rationales.`;
  }
  
  private async judgePairwise(
    outputs: Output[],
    judges: JudgeConfig[]
  ): Promise<void> {
    // Group by case
    const byCase = outputs.reduce((acc, output) => {
      const key = output.caseId;
      if (!acc[key]) acc[key] = [];
      acc[key].push(output);
      return acc;
    }, {} as Record<string, Output[]>);
    
    // Compare all pairs within each case
    for (const [caseId, caseOutputs] of Object.entries(byCase)) {
      if (caseOutputs.length < 2) continue;
      
      for (let i = 0; i < caseOutputs.length; i++) {
        for (let j = i + 1; j < caseOutputs.length; j++) {
          await Promise.all(
            judges.map((judge) =>
              this.comparePair(caseOutputs[i], caseOutputs[j], judge)
            )
          );
        }
      }
    }
  }
  
  private async comparePair(
    outputA: Output,
    outputB: Output,
    judge: JudgeConfig
  ): Promise<void> {
    // Randomize order to avoid position bias
    const [first, second] = Math.random() < 0.5
      ? [outputA, outputB]
      : [outputB, outputA];
    
    // Implementation similar to pointwise...
    // Parse winner, create judgment records
  }
}
```

### **6.3 Aggregator Service**

```typescript
// packages/api/src/services/aggregator.ts
import { PrismaClient } from '@prisma/client';

export class AggregatorService {
  constructor(private prisma: PrismaClient) {}
  
  async aggregateIteration(iterationId: string): Promise<any> {
    const iteration = await this.prisma.iteration.findUniqueOrThrow({
      where: { id: iterationId },
      include: {
        experiment: true,
        modelRuns: {
          include: {
            outputs: {
              include: {
                judgments: true,
              },
            },
          },
        },
      },
    });
    
    const rubric = iteration.experiment.rubric as Rubric;
    
    // Aggregate pointwise scores
    const compositeScores = this.calculateCompositeScores(
      iteration.modelRuns,
      rubric
    );
    
    // Calculate confidence intervals via bootstrap
    const confidenceIntervals = this.bootstrapCI(
      iteration.modelRuns,
      rubric,
      1000
    );
    
    // Pairwise ranking
    const pairwiseRanking = await this.calculatePairwiseRanking(iterationId);
    
    // Facet analysis (by tags, length, etc)
    const facetAnalysis = this.analyzeFacets(iteration.modelRuns);
    
    // Cost tracking
    const totalCost = iteration.modelRuns.reduce(
      (sum, run) => sum + run.costUsd,
      0
    );
    
    const totalTokens = iteration.modelRuns.reduce(
      (sum, run) => sum + run.tokensIn + run.tokensOut,
      0
    );
    
    return {
      compositeScores,
      confidenceIntervals,
      pairwiseRanking,
      facetAnalysis,
      totalCost,
      totalTokens,
      timestamp: new Date().toISOString(),
    };
  }
  
  private calculateCompositeScores(
    modelRuns: any[],
    rubric: Rubric
  ): Record<string, number> {
    const runScores: Record<string, number> = {};
    
    for (const run of modelRuns) {
      const criterionScores: Record<string, number[]> = {};
      
      // Collect all scores for each criterion
      for (const output of run.outputs) {
        for (const judgment of output.judgments) {
          if (judgment.mode !== 'POINTWISE') continue;
          
          for (const [criterion, score] of Object.entries(judgment.scores)) {
            if (!criterionScores[criterion]) {
              criterionScores[criterion] = [];
            }
            criterionScores[criterion].push(score as number);
          }
        }
      }
      
      // Calculate weighted composite
      let composite = 0;
      for (const criterion of rubric) {
        const scores = criterionScores[criterion.name] || [];
        const avg = scores.length > 0
          ? scores.reduce((a, b) => a + b, 0) / scores.length
          : 0;
        composite += avg * criterion.weight;
      }
      
      runScores[run.id] = composite;
    }
    
    return runScores;
  }
  
  private bootstrapCI(
    modelRuns: any[],
    rubric: Rubric,
    iterations: number = 1000
  ): Record<string, { lower: number; upper: number }> {
    const cis: Record<string, { lower: number; upper: number }> = {};
    
    for (const run of modelRuns) {
      const allScores = run.outputs.flatMap((o: any) =>
        o.judgments
          .filter((j: any) => j.mode === 'POINTWISE')
          .map((j: any) => {
            // Calculate weighted composite for this judgment
            let composite = 0;
            for (const criterion of rubric) {
              const score = j.scores[criterion.name] || 0;
              composite += score * criterion.weight;
            }
            return composite;
          })
      );
      
      if (allScores.length === 0) {
        cis[run.id] = { lower: 0, upper: 0 };
        continue;
      }
      
      const bootstrapMeans: number[] = [];
      
      for (let i = 0; i < iterations; i++) {
        const sample = [];
        for (let j = 0; j < allScores.length; j++) {
          const idx = Math.floor(Math.random() * allScores.length);
          sample.push(allScores[idx]);
        }
        const mean = sample.reduce((a, b) => a + b, 0) / sample.length;
        bootstrapMeans.push(mean);
      }
      
      bootstrapMeans.sort((a, b) => a - b);
      
      const lowerIdx = Math.floor(0.025 * iterations);
      const upperIdx = Math.floor(0.975 * iterations);
      
      cis[run.id] = {
        lower: bootstrapMeans[lowerIdx],
        upper: bootstrapMeans[upperIdx],
      };
    }
    
    return cis;
  }
  
  private async calculatePairwiseRanking(
    iterationId: string
  ): Promise<Record<string, number>> {
    // Bradley-Terry model implementation
    // For simplicity, use win rate
    
    const judgments = await this.prisma.judgment.findMany({
      where: {
        mode: 'PAIRWISE',
        output: {
          modelRun: {
            iterationId,
          },
        },
      },
      include: {
        output: {
          include: {
            modelRun: true,
          },
        },
      },
    });
    
    const wins: Record<string, number> = {};
    const total: Record<string, number> = {};
    
    for (const judgment of judgments) {
      const runId = judgment.output.modelRun.id;
      
      if (!wins[runId]) wins[runId] = 0;
      if (!total[runId]) total[runId] = 0;
      
      total[runId]++;
      
      if (judgment.winnerOutputId === judgment.outputId) {
        wins[runId]++;
      }
    }
    
    const ranking: Record<string, number> = {};
    for (const [runId, w] of Object.entries(wins)) {
      ranking[runId] = total[runId] > 0 ? w / total[runId] : 0;
    }
    
    return ranking;
  }
  
  private analyzeFacets(modelRuns: any[]): any {
    // Group outputs by tags, calculate avg scores per tag
    const facets: Record<string, { count: number; avgScore: number }> = {};
    
    // Implementation...
    
    return facets;
  }
}
```

### **6.4 Refiner Service**

```typescript
// packages/api/src/services/refiner.ts
import { PrismaClient } from '@prisma/client';
import { LLMAdapterFactory } from '@/llm/factory';
import * as diff from 'diff';

export class RefinerService {
  constructor(
    private prisma: PrismaClient,
    private adapterFactory: LLMAdapterFactory
  ) {}
  
  async refinePrompt(iterationId: string): Promise<string> {
    const iteration = await this.prisma.iteration.findUniqueOrThrow({
      where: { id: iterationId },
      include: {
        experiment: true,
        promptVersion: true,
        modelRuns: {
          include: {
            outputs: {
              include: {
                judgments: true,
                case: true,
              },
            },
          },
        },
      },
    });
    
    // 1. Identify weakest criteria
    const weakCriteria = this.identifyWeaknesses(
      iteration.modelRuns,
      iteration.experiment.rubric as Rubric
    );
    
    // 2. Find failing exemplars
    const failingExemplars = this.extractFailingExemplars(
      iteration.modelRuns,
      weakCriteria
    );
    
    // 3. Build refiner prompt
    const refinerPrompt = this.buildRefinerPrompt(
      iteration.experiment.goal,
      iteration.experiment.rubric as Rubric,
      iteration.promptVersion.text,
      weakCriteria,
      failingExemplars
    );
    
    // 4. Call refiner LLM
    const credential = await this.prisma.providerCredential.findFirstOrThrow({
      where: {
        projectId: iteration.experiment.projectId,
        provider: 'ANTHROPIC', // Use Claude for refinement
        isActive: true,
      },
    });
    
    const adapter = await this.adapterFactory.getAdapter(
      credential,
      'claude-sonnet-4'
    );
    
    const response = await adapter.chat([
      {
        role: 'system',
        content: `You are an expert prompt engineer. Your task is to propose targeted, minimal edits to improve prompts.
        
Rules:
- Make SMALL, surgical changes
- Focus only on the weak criteria
- Keep all constraints and requirements
- Return ONLY a unified diff (git format)
- Add a brief note explaining the changes`,
      },
      { role: 'user', content: refinerPrompt },
    ], {
      params: { temperature: 0.7, maxTokens: 2000 },
    });
    
    // 5. Parse diff and note
    const { diff: unifiedDiff, note } = this.parseDiffResponse(response.text);
    
    // 6. Validate diff
    const isValid = this.validateDiff(
      iteration.promptVersion.text,
      unifiedDiff
    );
    
    if (!isValid) {
      throw new Error('Generated diff is invalid or too aggressive');
    }
    
    // 7. Create suggestion
    const suggestion = await this.prisma.suggestion.create({
      data: {
        promptVersionId: iteration.promptVersionId,
        source: 'refiner_llm',
        diffUnified: unifiedDiff,
        note,
        targetCriteria: weakCriteria.map((c) => c.name),
        status: 'PENDING',
      },
    });
    
    return suggestion.id;
  }
  
  private identifyWeaknesses(
    modelRuns: any[],
    rubric: Rubric
  ): RubricCriterion[] {
    const criterionScores: Record<string, number[]> = {};
    
    for (const run of modelRuns) {
      for (const output of run.outputs) {
        for (const judgment of output.judgments) {
          if (judgment.mode !== 'POINTWISE') continue;
          
          for (const [criterion, score] of Object.entries(judgment.scores)) {
            if (!criterionScores[criterion]) {
              criterionScores[criterion] = [];
            }
            criterionScores[criterion].push(score as number);
          }
        }
      }
    }
    
    // Calculate avg score per criterion
    const avgScores = Object.entries(criterionScores).map(([name, scores]) => ({
      name,
      avgScore: scores.reduce((a, b) => a + b, 0) / scores.length,
    }));
    
    // Return bottom 2 criteria
    avgScores.sort((a, b) => a.avgScore - b.avgScore);
    const weakNames = avgScores.slice(0, 2).map((s) => s.name);
    
    return rubric.filter((c) => weakNames.includes(c.name));
  }
  
  private extractFailingExemplars(
    modelRuns: any[],
    weakCriteria: RubricCriterion[]
  ): any[] {
    const exemplars: any[] = [];
    
    for (const run of modelRuns) {
      for (const output of run.outputs) {
        const judgments = output.judgments.filter(
          (j: any) => j.mode === 'POINTWISE'
        );
        
        if (judgments.length === 0) continue;
        
        // Check if this output scores low on weak criteria
        const isWeak = weakCriteria.some((criterion) => {
          const scores = judgments.map(
            (j: any) => j.scores[criterion.name] || 0
          );
          const avg = scores.reduce((a: number, b: number) => a + b, 0) / scores.length;
          return avg < 2.5; // Below midpoint
        });
        
        if (isWeak) {
          exemplars.push({
            input: output.case.input,
            output: output.rawText,
            scores: judgments[0].scores,
            rationales: judgments[0].rationales,
          });
        }
      }
    }
    
    // Return top 5 worst exemplars
    return exemplars.slice(0, 5);
  }
  
  private buildRefinerPrompt(
    goal: string,
    rubric: Rubric,
    currentPrompt: string,
    weakCriteria: RubricCriterion[],
    failingExemplars: any[]
  ): string {
    return `# Prompt Refinement Task

## Goal
${goal}

## Current Prompt
\`\`\`
${currentPrompt}
\`\`\`

## Weak Criteria
${weakCriteria.map((c) => `- **${c.name}**: ${c.description}`).join('\n')}

## Failing Exemplars
${failingExemplars.map((ex, i) => `
### Example ${i + 1}
Input: ${JSON.stringify(ex.input)}
Output: ${ex.output}
Scores: ${JSON.stringify(ex.scores)}
Issues: ${Object.entries(ex.rationales)
  .filter(([k]) => weakCriteria.some((c) => c.name === k))
  .map(([k, v]) => `${k}: ${v}`)
  .join('; ')}
`).join('\n')}

## Task
Propose SMALL, targeted edits to the prompt to improve the weak criteria.

Requirements:
- Keep all existing constraints and requirements
- Make minimal changes (< 10% of text)
- Focus on clarity and specificity for weak criteria
- Do not change the core structure

Return your response in this format:

<diff>
[unified diff in git format]
</diff>

<note>
[1 paragraph explaining the changes and how they address the weak criteria]
</note>`;
  }
  
  private parseDiffResponse(response: string): { diff: string; note: string } {
    const diffMatch = response.match(/<diff>(.*?)<\/diff>/s);
    const noteMatch = response.match(/<note>(.*?)<\/note>/s);
    
    return {
      diff: diffMatch?.[1].trim() || '',
      note: noteMatch?.[1].trim() || '',
    };
  }
  
  private validateDiff(original: string, unifiedDiff: string): boolean {
    try {
      // Apply diff and check result
      const patches = diff.parsePatch(unifiedDiff);
      if (patches.length === 0) return false;
      
      const result = diff.applyPatch(original, patches[0]);
      if (!result) return false;
      
      // Check length delta
      const lengthDelta = Math.abs(result.length - original.length);
      const maxDelta = original.length * 0.15; // Max 15% change
      
      if (lengthDelta > maxDelta) return false;
      
      return true;
    } catch (error) {
      return false;
    }
  }
  
  async applyDiff(suggestionId: string): Promise<string> {
    const suggestion = await this.prisma.suggestion.findUniqueOrThrow({
      where: { id: suggestionId },
      include: { promptVersion: true },
    });
    
    const patches = diff.parsePatch(suggestion.diffUnified);
    const newText = diff.applyPatch(
      suggestion.promptVersion.text,
      patches[0]
    );
    
    if (!newText) {
      throw new Error('Failed to apply diff');
    }
    
    // Create new prompt version
    const newVersion = await this.prisma.promptVersion.create({
      data: {
        experimentId: suggestion.promptVersion.experimentId,
        version: suggestion.promptVersion.version + 1,
        parentId: suggestion.promptVersionId,
        text: newText,
        systemText: suggestion.promptVersion.systemText,
        fewShots: suggestion.promptVersion.fewShots,
        toolsSchema: suggestion.promptVersion.toolsSchema,
        changelog: suggestion.note,
        createdBy: null, // System-generated
      },
    });
    
    // Mark suggestion as applied
    await this.prisma.suggestion.update({
      where: { id: suggestionId },
      data: { status: 'APPLIED' },
    });
    
    return newVersion.id;
  }
}
```

### **6.5 Generator Service (Datasets)**

```typescript
// packages/api/src/services/generator.ts
import { PrismaClient, DatasetKind } from '@prisma/client';
import { LLMAdapterFactory } from '@/llm/factory';

export class GeneratorService {
  constructor(
    private prisma: PrismaClient,
    private adapterFactory: LLMAdapterFactory
  ) {}
  
  async generateSyntheticCases(
    projectId: string,
    spec: {
      count: number;
      diversity: number; // 0-1
      domainHints: string;
      languages?: string[];
      lengthBuckets?: string[];
    }
  ): Promise<string> {
    // 1. Create dataset
    const dataset = await this.prisma.dataset.create({
      data: {
        projectId,
        name: `Synthetic ${new Date().toISOString()}`,
        kind: 'SYNTHETIC',
        metadata: { spec },
      },
    });
    
    // 2. Generate cases in batches
    const batchSize = 20;
    const batches = Math.ceil(spec.count / batchSize);
    
    for (let i = 0; i < batches; i++) {
      const batchCount = Math.min(batchSize, spec.count - i * batchSize);
      
      const cases = await this.generateBatch(
        spec.domainHints,
        batchCount,
        spec.diversity
      );
      
      // Deduplicate
      const unique = await this.deduplicateCases(cases);
      
      // Save to DB
      await this.prisma.case.createMany({
        data: unique.map((c) => ({
          datasetId: dataset.id,
          input: c.input,
          tags: c.tags || [],
          difficulty: c.difficulty || 3,
        })),
      });
    }
    
    return dataset.id;
  }
  
  private async generateBatch(
    domainHints: string,
    count: number,
    diversity: number
  ): Promise<any[]> {
    const credential = await this.prisma.providerCredential.findFirstOrThrow({
      where: {
        provider: 'OPENAI',
        isActive: true,
      },
    });
    
    const adapter = await this.adapterFactory.getAdapter(
      credential,
      'gpt-4o-mini' // Use cheaper model for generation
    );
    
    const prompt = `Generate ${count} diverse test cases for this domain:

${domainHints}

Requirements:
- Vary complexity, entities, phrasing
- Diversity level: ${diversity * 10}/10
- Include edge cases and ambiguous inputs
- Return ONLY valid JSON array:

[
  {
    "input": {<input_json>},
    "tags": ["tag1", "tag2"],
    "difficulty": 1-5
  }
]`;
    
    const response = await adapter.chat([
      { role: 'user', content: prompt },
    ], {
      params: { temperature: 0.8 + diversity * 0.2 },
    });
    
    return JSON.parse(response.text);
  }
  
  private async deduplicateCases(cases: any[]): Promise<any[]> {
    // Simple dedup by exact input match
    // In production, use embeddings + cosine similarity
    
    const seen = new Set<string>();
    const unique: any[] = [];
    
    for (const c of cases) {
      const key = JSON.stringify(c.input);
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(c);
      }
    }
    
    return unique;
  }
  
  async generateAdversarialCases(
    experimentId: string,
    targetCount: number
  ): Promise<string> {
    // 1. Analyze coverage gaps from existing iterations
    const gaps = await this.analyzeCoverageGaps(experimentId);
    
    // 2. Generate cases targeting gaps
    // Implementation similar to synthetic generation,
    // but with focus on failure patterns
    
    // ...
    
    return 'dataset-id';
  }
  
  private async analyzeCoverageGaps(experimentId: string): Promise<any> {
    // Facet analysis to find underrepresented areas
    // Return gaps like: {tags: [], lengthRanges: [], entities: []}
  }
}
```

-----

## **7. Job Queue (BullMQ)**

```typescript
// packages/api/src/queue/workers/execute.worker.ts
import { Worker, Job } from 'bullmq';
import { PrismaClient } from '@prisma/client';
import { LLMAdapterFactory } from '@/llm/factory';
import { redis } from '@/lib/redis';

const prisma = new PrismaClient();
const adapterFactory = new LLMAdapterFactory();

const worker = new Worker(
  'execute-run',
  async (job: Job) => {
    const { modelRunId } = job.data;
    
    await prisma.modelRun.update({
      where: { id: modelRunId },
      data: { status: 'RUNNING', startedAt: new Date() },
    });
    
    try {
      const modelRun = await prisma.modelRun.findUniqueOrThrow({
        where: { id: modelRunId },
        include: {
          promptVersion: true,
          modelConfig: true,
          iteration: {
            include: {
              experiment: {
                include: {
                  project: {
                    include: {
                      providers: true,
                    },
                  },
                },
              },
            },
          },
        },
      });
      
      // Get all cases for this run
      const cases = await prisma.case.findMany({
        where: { datasetId: modelRun.datasetId },
      });
      
      // Get adapter
      const credential = modelRun.iteration.experiment.project.providers.find(
        (p) => p.provider === modelRun.modelConfig.provider
      );
      
      if (!credential) {
        throw new Error('Provider credential not found');
      }
      
      const adapter = await adapterFactory.getAdapter(
        credential,
        modelRun.modelConfig.modelId
      );
      
      // Execute for each case
      let totalTokensIn = 0;
      let totalTokensOut = 0;
      let totalCost = 0;
      
      for (const testCase of cases) {
        // Build messages
        const messages = [
          {
            role: 'system' as const,
            content: modelRun.promptVersion.systemText || '',
          },
          {
            role: 'user' as const,
            content: renderPrompt(
              modelRun.promptVersion.text,
              testCase.input
            ),
          },
        ];
        
        // Execute
        const response = await adapter.chat(messages, {
          params: modelRun.modelConfig.params as any,
          seed: modelRun.modelConfig.seed || undefined,
        });
        
        // Save output
        await prisma.output.create({
          data: {
            modelRunId,
            caseId: testCase.id,
            rawText: response.text,
            parsed: null,
            tokensOut: response.usage.completionTokens,
            latencyMs: response.latencyMs,
            cached: response.cached,
          },
        });
        
        totalTokensIn += response.usage.promptTokens;
        totalTokensOut += response.usage.completionTokens;
        totalCost += adapter.estimateCost(
          response.usage.promptTokens,
          response.usage.completionTokens
        );
        
        // Update progress
        await job.updateProgress({
          completed: cases.indexOf(testCase) + 1,
          total: cases.length,
        });
      }
      
      // Update run
      await prisma.modelRun.update({
        where: { id: modelRunId },
        data: {
          status: 'COMPLETED',
          tokensIn: totalTokensIn,
          tokensOut: totalTokensOut,
          costUsd: totalCost,
          finishedAt: new Date(),
        },
      });
      
      // Track cost
      await prisma.costTracking.create({
        data: {
          projectId: modelRun.iteration.experiment.projectId,
          provider: modelRun.modelConfig.provider,
          modelId: modelRun.modelConfig.modelId,
          tokensIn: totalTokensIn,
          tokensOut: totalTokensOut,
          costUsd: totalCost,
        },
      });
      
    } catch (error) {
      await prisma.modelRun.update({
        where: { id: modelRunId },
        data: {
          status: 'FAILED',
          errorMessage: error.message,
          finishedAt: new Date(),
        },
      });
      
      throw error;
    }
  },
  {
    connection: redis,
    concurrency: 5, // Process 5 runs concurrently
  }
);

function renderPrompt(template: string, variables: any): string {
  // Simple template rendering
  let result = template;
  for (const [key, value] of Object.entries(variables)) {
    result = result.replace(
      new RegExp(`{{\\s*${key}\\s*}}`, 'g'),
      String(value)
    );
  }
  return result;
}

worker.on('completed', async (job) => {
  console.log(`Job ${job.id} completed`);
  // Notify orchestrator
});

worker.on('failed', (job, err) => {
  console.error(`Job ${job?.id} failed:`, err);
});
```

Create similar workers for:

- `judge.worker.ts`
- `refine.worker.ts`
- `aggregate.worker.ts`
- `generate.worker.ts`

-----

## **8. API Layer (tRPC)**

```typescript
// packages/api/src/trpc/routers/experiment.router.ts
import { z } from 'zod';
import { router, protectedProcedure } from '../trpc';
import { TRPCError } from '@trpc/server';
import { RubricSchema, StopRulesSchema } from '@packages/shared';

export const experimentRouter = router({
  create: protectedProcedure
    .input(z.object({
      projectId: z.string(),
      name: z.string().min(1).max(200),
      description: z.string().optional(),
      goal: z.string().min(10),
      rubric: RubricSchema,
      stopRules: StopRulesSchema,
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
      
      return ctx.prisma.experiment.create({
        data: {
          projectId: input.projectId,
          name: input.name,
          description: input.description,
          goal: input.goal,
          rubric: input.rubric,
          stopRules: input.stopRules,
          status: 'DRAFT',
        },
      });
    }),
  
  get: protectedProcedure
    .input(z.object({ id: z.string() }))
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
            take: 5,
          },
        },
      });
      
      if (!experiment || experiment.project.members.length === 0) {
        throw new TRPCError({ code: 'NOT_FOUND' });
      }
      
      return experiment;
    }),
  
  run: protectedProcedure
    .input(z.object({
      experimentId: z.string(),
      promptVersionId: z.string().optional(),
    }))
    .mutation(async ({ input, ctx }) => {
      const experiment = await ctx.prisma.experiment.findUniqueOrThrow({
        where: { id: input.experimentId },
        include: {
          project: {
            include: {
              members: { where: { userId: ctx.user.id } },
            },
          },
        },
      });
      
      if (experiment.project.members.length === 0) {
        throw new TRPCError({ code: 'FORBIDDEN' });
      }
      
      // Get or create prompt version
      let promptVersionId = input.promptVersionId;
      
      if (!promptVersionId) {
        const latestVersion = await ctx.prisma.promptVersion.findFirst({
          where: { experimentId: input.experimentId },
          orderBy: { version: 'desc' },
        });
        
        if (!latestVersion) {
          throw new TRPCError({
            code: 'BAD_REQUEST',
            message: 'No prompt version found',
          });
        }
        
        promptVersionId = latestVersion.id;
      }
      
      // Start iteration via orchestrator
      const iterationId = await ctx.orchestrator.startIteration(
        input.experimentId,
        promptVersionId
      );
      
      return { iterationId };
    }),
  
  // More procedures: update, delete, listIterations, etc.
});

// packages/api/src/trpc/routers/prompt.router.ts
export const promptRouter = router({
  create: protectedProcedure
    .input(z.object({
      experimentId: z.string(),
      text: z.string().min(10),
      systemText: z.string().optional(),
    }))
    .mutation(async ({ input, ctx }) => {
      const experiment = await ctx.prisma.experiment.findUniqueOrThrow({
        where: { id: input.experimentId },
      });
      
      const lastVersion = await ctx.prisma.promptVersion.findFirst({
        where: { experimentId: input.experimentId },
        orderBy: { version: 'desc' },
      });
      
      return ctx.prisma.promptVersion.create({
        data: {
          experimentId: input.experimentId,
          version: (lastVersion?.version || 0) + 1,
          text: input.text,
          systemText: input.systemText,
          createdBy: ctx.user.id,
        },
      });
    }),
  
  // AI assist procedures
  draft: protectedProcedure
    .input(z.object({
      experimentId: z.string(),
      count: z.number().int().min(1).max(5).default(3),
    }))
    .mutation(async ({ input, ctx }) => {
      const experiment = await ctx.prisma.experiment.findUniqueOrThrow({
        where: { id: input.experimentId },
      });
      
      // Generate draft prompts using AI
      const drafts = await ctx.aiAssist.draftPrompts(
        experiment.goal,
        experiment.rubric,
        input.count
      );
      
      return drafts;
    }),
  
  improve: protectedProcedure
    .input(z.object({
      promptVersionId: z.string(),
      focus: z.array(z.string()).optional(),
    }))
    .mutation(async ({ input, ctx }) => {
      // Generate improvement suggestions
      // Return diff preview
    }),
});

// Combine all routers
export const appRouter = router({
  project: projectRouter,
  experiment: experimentRouter,
  prompt: promptRouter,
  dataset: datasetRouter,
  run: runRouter,
  review: reviewRouter,
});

export type AppRouter = typeof appRouter;
```

-----

## **9. Frontend Architecture**

### **9.1 Project Structure**

```
apps/web/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── signup/
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── projects/
│   │   │   ├── page.tsx
│   │   │   └── [slug]/
│   │   │       ├── page.tsx
│   │   │       ├── settings/
│   │   │       └── experiments/
│   │   │           ├── page.tsx
│   │   │           ├── new/page.tsx (Wizard)
│   │   │           └── [id]/
│   │   │               ├── page.tsx (Overview)
│   │   │               ├── runs/
│   │   │               ├── prompts/
│   │   │               ├── datasets/
│   │   │               └── reviews/
│   ├── api/
│   │   └── trpc/[trpc]/route.ts
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/ (shadcn components)
│   ├── experiment/
│   │   ├── wizard/
│   │   ├── run-viewer/
│   │   ├── diff-viewer/
│   │   └── sxs-viewer/
│   ├── ai-assist/
│   └── charts/
├── lib/
│   ├── trpc.ts
│   └── utils.ts
└── package.json
```

### **9.2 Key Components**

**Experiment Wizard (Multistep Form)**

```typescript
// components/experiment/wizard/wizard.tsx
'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ObjectiveStep } from './steps/objective';
import { RubricStep } from './steps/rubric';
import { PromptStep } from './steps/prompt';
import { DatasetStep } from './steps/dataset';
import { ModelsStep } from './steps/models';
import { JudgesStep } from './steps/judges';
import { StopRulesStep } from './steps/stop-rules';

const steps = [
  { id: 'objective', title: 'Objective', component: ObjectiveStep },
  { id: 'rubric', title: 'Rubric', component: RubricStep },
  { id: 'prompt', title: 'Seed Prompt', component: PromptStep },
  { id: 'datasets', title: 'Test Data', component: DatasetStep },
  { id: 'models', title: 'Models', component: ModelsStep },
  { id: 'judges', title: 'Judges', component: JudgesStep },
  { id: 'stop', title: 'Stop Rules', component: StopRulesStep },
];

export function ExperimentWizard({ projectId }: { projectId: string }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Partial<ExperimentInput>>({});
  
  const CurrentStepComponent = steps[currentStep].component;
  
  const handleNext = (stepData: any) => {
    setFormData({ ...formData, ...stepData });
    
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Submit final form
      handleSubmit();
    }
  };
  
  const handleSubmit = async () => {
    // Create experiment via tRPC
    await trpc.experiment.create.mutate({
      projectId,
      ...formData,
    });
  };
  
  return (
    <div className="max-w-4xl mx-auto py-12">
      <Progress value={((currentStep + 1) / steps.length) * 100} />
      
      <div className="mt-8">
        <h2 className="text-2xl font-semibold mb-2">
          {steps[currentStep].title}
        </h2>
        
        <CurrentStepComponent
          data={formData}
          onNext={handleNext}
          onBack={() => setCurrentStep(Math.max(0, currentStep - 1))}
        />
      </div>
    </div>
  );
}
```

**AI Assist Bar (Reusable Pattern)**

```typescript
// components/ai-assist/assist-bar.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Sparkles, ChevronDown } from 'lucide-react';
import { trpc } from '@/lib/trpc';

interface AIAssistBarProps {
  type: 'objective' | 'rubric' | 'prompt' | 'dataset';
  experimentId?: string;
  onInsert: (content: any) => void;
}

export function AIAssistBar({ type, experimentId, onInsert }: AIAssistBarProps) {
  const [showOptions, setShowOptions] = useState(false);
  const [drafts, setDrafts] = useState<any[]>([]);
  
  const draftMutation = trpc.aiAssist.draft.useMutation({
    onSuccess: (data) => {
      setDrafts(data);
      setShowOptions(true);
    },
  });
  
  return (
    <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg">
      <Sparkles className="w-4 h-4 text-teal-600" />
      <span className="text-sm text-slate-600 font-medium">AI Assist</span>
      
      <div className="flex-1" />
      
      <Button
        size="sm"
        variant="outline"
        onClick={() => draftMutation.mutate({ type, experimentId, count: 3 })}
        isLoading={draftMutation.isLoading}
      >
        Draft
      </Button>
      
      <Button size="sm" variant="outline">
        Complete
      </Button>
      
      <Button size="sm" variant="outline">
        Improve
      </Button>
      
      {showOptions && (
        <div className="absolute mt-2 w-full bg-white shadow-lg rounded-lg p-4">
          <h4 className="font-medium mb-3">Choose a draft:</h4>
          {drafts.map((draft, i) => (
            <div
              key={i}
              className="p-3 border rounded hover:bg-slate-50 cursor-pointer mb-2"
              onClick={() => {
                onInsert(draft);
                setShowOptions(false);
              }}
            >
              {draft.preview}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Diff Viewer**

```typescript
// components/experiment/diff-viewer.tsx
'use client';

import { parseDiff, Diff, Hunk } from 'react-diff-view';
import 'react-diff-view/style/index.css';

interface DiffViewerProps {
  oldText: string;
  newText: string;
  unified?: string;
}

export function DiffViewer({ oldText, newText, unified }: DiffViewerProps) {
  const files = unified
    ? parseDiff(unified)
    : parseDiff(createUnifiedDiff(oldText, newText));
  
  return (
    <div className="font-mono text-sm">
      {files.map((file, i) => (
        <Diff key={i} viewType="split" diffType={file.type} hunks={file.hunks}>
          {(hunks) =>
            hunks.map((hunk) => <Hunk key={hunk.content} hunk={hunk} />)
          }
        </Diff>
      ))}
    </div>
  );
}

function createUnifiedDiff(oldText: string, newText: string): string {
  // Use diff library to create unified diff
  const Diff = require('diff');
  const patch = Diff.createTwoFilesPatch(
    'old',
    'new',
    oldText,
    newText,
    '',
    ''
  );
  return patch;
}
```

**Run Timeline (Real-time Updates)**

```typescript
// components/experiment/run-viewer/timeline.tsx
'use client';

import { useEffect, useState } from 'react';
import { trpc } from '@/lib/trpc';

export function RunTimeline({ iterationId }: { iterationId: string }) {
  const [events, setEvents] = useState<any[]>([]);
  
  useEffect(() => {
    // Subscribe to SSE for real-time updates
    const eventSource = new EventSource(
      `/api/iterations/${iterationId}/stream`
    );
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
    };
    
    return () => eventSource.close();
  }, [iterationId]);
  
  return (
    <div className="space-y-4">
      {events.map((event, i) => (
        <TimelineEvent key={i} event={event} />
      ))}
    </div>
  );
}
```

-----

## **10. Implementation Plan**

### **Phase 1: Foundation (Week 1-2)**

- [ ] Set up monorepo with pnpm workspaces
- [ ] Configure TypeScript, ESLint, Prettier
- [ ] Initialize Next.js app with App Router
- [ ] Set up Prisma with initial schema
- [ ] Create Docker Compose with Postgres + Redis
- [ ] Implement auth (JWT + bcrypt)
- [ ] Set up tRPC with basic routers
- [ ] Create UI design system (tokens, components)

### **Phase 2: Core Data & LLM (Week 3-4)**

- [ ] Finish Prisma schema + migrations
- [ ] Implement LLM adapter system (OpenAI, Anthropic)
- [ ] Add caching layer with Redis
- [ ] Create provider credential encryption
- [ ] Build adapter factory + testing

### **Phase 3: Orchestration (Week 5-6)**

- [ ] Set up BullMQ with workers
- [ ] Implement IterationOrchestrator
- [ ] Create execute worker (run prompts)
- [ ] Build EvaluatorService (pointwise judging)
- [ ] Add AggregatorService (composite scores)

### **Phase 4: UI - Experiment Creation (Week 7-8)**

- [ ] Build wizard shell with steps
- [ ] Objective step + AI assist
- [ ] Rubric editor with validation
- [ ] Prompt editor with Monaco
- [ ] Dataset upload + mapper
- [ ] Model/judge configuration
- [ ] Wire up to tRPC mutations

### **Phase 5: Execution & Viewing (Week 9-10)**

- [ ] Run button + iteration start
- [ ] Real-time timeline with SSE
- [ ] Side-by-side output viewer
- [ ] Judgment display with rationales
- [ ] Metrics dashboard with charts
- [ ] Cost tracking UI

### **Phase 6: Refinement Loop (Week 11-12)**

- [ ] Implement RefinerService
- [ ] Build diff viewer component
- [ ] Create HITL review queue
- [ ] Add approve/reject workflow
- [ ] Apply diff + create new version
- [ ] Stop rules enforcement

### **Phase 7: Advanced Features (Week 13-14)**

- [ ] Pairwise judging + ranking
- [ ] Bootstrap CI calculation
- [ ] Synthetic dataset generation
- [ ] Adversarial case generation
- [ ] Coverage analysis + heatmap
- [ ] Export bundle functionality

### **Phase 8: Polish & Optimization (Week 15-16)**

- [ ] Add comprehensive error handling
- [ ] Implement retry logic everywhere
- [ ] Add loading skeletons
- [ ] Optimize queries (add indexes)
- [ ] Add OpenTelemetry tracing
- [ ] Write integration tests
- [ ] Accessibility audit
- [ ] Performance profiling
- [ ] Documentation

-----

## **11. Critical Implementation Details**

### **11.1 Cost Control**

```typescript
// packages/api/src/services/budget-enforcer.ts
export class BudgetEnforcer {
  async checkBudget(experimentId: string): Promise<void> {
    const experiment = await prisma.experiment.findUniqueOrThrow({
      where: { id: experimentId },
    });
    
    const stopRules = experiment.stopRules as StopRules;
    
    if (!stopRules.maxBudgetUsd) return;
    
    // Get total spend
    const totalSpend = await prisma.costTracking.aggregate({
      where: {
        projectId: experiment.projectId,
        timestamp: { gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) },
      },
      _sum: { costUsd: true },
    });
    
    if ((totalSpend._sum.costUsd || 0) >= stopRules.maxBudgetUsd) {
      throw new Error('Budget exceeded');
    }
  }
  
  async estimateIterationCost(
    experimentId: string,
    promptVersionId: string
  ): Promise<number> {
    // Estimate based on prompt length + dataset size + models
    // Return estimated cost in USD
  }
}
```

### **11.2 Early Stopping**

```typescript
// In Orchestrator
private async checkStopRules(iterationId: string): Promise<boolean> {
  const iteration = await this.prisma.iteration.findUniqueOrThrow({
    where: { id: iterationId },
    include: { experiment: true },
  });
  
  const stopRules = iteration.experiment.stopRules as StopRules;
  const metrics = iteration.metrics as any;
  
  // Check max iterations
  if (iteration.number >= stopRules.maxIterations) {
    return true;
  }
  
  // Check convergence (no improvement for N iterations)
  const recentIterations = await this.prisma.iteration.findMany({
    where: {
      experimentId: iteration.experimentId,
      number: {
        gte: iteration.number - stopRules.convergenceWindow,
        lt: iteration.number,
      },
    },
    orderBy: { number: 'desc' },
  });
  
  if (recentIterations.length >= stopRules.convergenceWindow) {
    const scores = recentIterations.map(
      (it) => (it.metrics as any).compositeScore
    );
    const currentScore = metrics.compositeScore;
    
    const maxPrevScore = Math.max(...scores);
    const delta = currentScore - maxPrevScore;
    
    if (delta < stopRules.minDeltaThreshold) {
      return true; // Converged
    }
  }
  
  return false;
}
```

### **11.3 Template System**

```typescript
// Pre-built experiment templates
export const templates: Record<string, ExperimentTemplate> = {
  'customer-support': {
    name: 'Customer Support Bot',
    goal: 'Generate helpful, empathetic responses to customer inquiries',
    rubric: [
      {
        name: 'Helpfulness',
        description: 'Provides actionable solution',
        weight: 0.35,
        scale: { min: 0, max: 5 },
      },
      {
        name: 'Empathy',
        description: 'Acknowledges customer emotions',
        weight: 0.25,
        scale: { min: 0, max: 5 },
      },
      {
        name: 'Accuracy',
        description: 'Factually correct information',
        weight: 0.25,
        scale: { min: 0, max: 5 },
      },
      {
        name: 'Conciseness',
        description: 'Clear and brief',
        weight: 0.15,
        scale: { min: 0, max: 5 },
      },
    ],
    seedPrompt: `You are a customer support agent. Help customers with...`,
    sampleCases: [
      // Pre-populated test cases
    ],
  },
  // More templates...
};
```

-----

## **12. Testing Strategy**

```typescript
// packages/api/tests/services/evaluator.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { EvaluatorService } from '@/services/evaluator';
import { MockLLMAdapter } from '../mocks/llm-adapter';

describe('EvaluatorService', () => {
  let service: EvaluatorService;
  let mockAdapter: MockLLMAdapter;
  
  beforeEach(() => {
    mockAdapter = new MockLLMAdapter();
    service = new EvaluatorService(prisma, mockAdapterFactory);
  });
  
  it('should judge output pointwise', async () => {
    mockAdapter.mockResponse({
      text: JSON.stringify({
        scores: { Helpfulness: 4, Accuracy: 5 },
        rationales: {
          Helpfulness: 'Good suggestions',
          Accuracy: 'All facts correct',
        },
        safetyFlags: {
          policyViolation: false,
          piiDetected: false,
          toxicContent: false,
          jailbreakAttempt: false,
        },
      }),
    });
    
    await service.judgeOutputs([outputId], [judgeConfig]);
    
    const judgment = await prisma.judgment.findFirst({
      where: { outputId },
    });
    
    expect(judgment?.scores).toEqual({
      Helpfulness: 4,
      Accuracy: 5,
    });
  });
});
```

-----

## **13. Deployment**

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: edison
      POSTGRES_USER: edison
      POSTGRES_PASSWORD: changeme
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: api
    environment:
      DATABASE_URL: postgresql://edison:changeme@db:5432/edison
      REDIS_URL: redis://redis:6379
      NODE_ENV: production
    ports:
      - "8080:8080"
    depends_on:
      - db
      - redis
  
  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: worker
    environment:
      DATABASE_URL: postgresql://edison:changeme@db:5432/edison
      REDIS_URL: redis://redis:6379
    depends_on:
      - db
      - redis
    deploy:
      replicas: 3
  
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: web
    environment:
      NEXT_PUBLIC_API_URL: http://api:8080
    ports:
      - "3000:3000"
    depends_on:
      - api

volumes:
  postgres_data:
```

```dockerfile
# Dockerfile
FROM node:20-alpine AS base
RUN corepack enable

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

# API target
FROM base AS api
WORKDIR /app
COPY --from=builder /app/packages/api/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/index.js"]

# Worker target
FROM base AS worker
WORKDIR /app
COPY --from=builder /app/packages/api/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/worker.js"]

# Web target
FROM base AS web
WORKDIR /app
COPY --from=builder /app/apps/web/.next ./.next
COPY --from=builder /app/apps/web/public ./public
COPY --from=builder /app/node_modules ./node_modules
CMD ["pnpm", "start"]
```

-----

## **14. Key Files to Create**

1. **`package.json`** (root): Workspace config
1. **`packages/shared/src/schemas/`**: All Zod schemas
1. **`packages/api/src/llm/`**: Adapter system
1. **`packages/api/src/services/`**: Core business logic
1. **`packages/api/src/queue/workers/`**: BullMQ workers
1. **`packages/api/src/trpc/routers/`**: API routes
1. **`apps/web/app/`**: Next.js pages
1. **`apps/web/components/`**: Reusable UI
1. **`prisma/schema.prisma`**: Full database schema
1. **`.env.example`**: Environment variables template

-----

## **Summary: You’re Building…**

A **production-grade prompt engineering platform** with:

- ✅ **Type-safe** end-to-end (Zod + TypeScript + tRPC)
- ✅ **Multi-provider LLM** support with caching
- ✅ **Ensemble judging** (pointwise + pairwise + safety)
- ✅ **Statistical rigor** (bootstrap CIs, rankings)
- ✅ **Diff-based refinement** (transparent changes)
- ✅ **Human-in-the-loop** (review queue, approval workflow)
- ✅ **AI-assisted authoring** (Draft/Complete/Improve)
- ✅ **Coverage-guided testing** (synthetic + adversarial datasets)
- ✅ **Cost controls** (budgets, early stopping, estimates)
- ✅ **Real-time updates** (SSE, job queue, progress tracking)
- ✅ **Beautiful UX** (shadcn/ui, Framer Motion, skeleton loaders)
- ✅ **Observable** (OpenTelemetry, structured logs, audit trail)
- ✅ **Testable** (unit + integration + E2E)
- ✅ **Deployable** (Docker Compose, single VPS or cloud)

**Now go build it.** Follow the phases, test relentlessly, and ship something people love. 🚀​​​​​​​​​​​​​​​​

CRITICAL: the end result should be a production application with all the features implemented. you must have implemented all the features in a production-ready way, and you must have tested and validated all features, implementations and user journeys. The project should be ready for deployment/usage with clear documentation and 100% un-mocked and reliable, no-bulshit tests implemented and validated.