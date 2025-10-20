# Edison Delivery Tracker

_Last updated: 2025-10-18_

This document is the single source of truth for Edison’s delivery status. Every contributor **must update this file** whenever work is completed, scope changes, or new risks emerge.

---

## 1. Current Snapshot

- **Build/Test Status**
  - `pnpm --filter @edison/web build` → ✅ passes (Next build + type checking clean after Tailwind + TS fixes).
  - `pnpm --filter @edison/web exec tsc --noEmit` → ✅ (shared type errors resolved, local `diff` declarations in place).
  - `pnpm --filter @edison/shared build` → ✅ (bundler-aware tsconfig produces CJS/ESM bundles + declarations).
  - `pnpm --filter @edison/api build` → ✅ (tsup + `tsc -p tsconfig.build.json` now emit JS and `.d.ts` artifacts).
  - `pnpm --filter @edison/api test` → ✅ passes (Vitest suites still limited to targeted units).
  - `DATABASE_URL=postgresql://edison:password@localhost:5432/edison pnpm --filter @edison/api prisma migrate deploy` → ✅ applies schema (two migrations).
  - `pnpm db:seed` → ✅ seeds admin/project/dataset/experiment when Postgres is up; script guides if DB or schema missing.
  - No Playwright or end-to-end validation configured.
- **Runtime**
  - `docker compose up` starts services; telemetry + Redis connection regressions resolved, but orchestration still incomplete so queues cannot finish an iteration.
  - Initial Prisma migration (`20251018140000_init`) authored; `pnpm db:seed` now provisions demo data once Postgres is reachable (script gracefully errors if DB is offline or creds wrong).
- **Frontend**
  - Tailwind pipeline now wired up, but dashboard pages depend on API endpoints and orchestration data that are not yet functional. Styling incomplete relative to shadcn/ui spec.
- **Backend**
  - Prisma client regenerated against committed schema; JSON helpers added to satisfy Prisma 5 input types; type-level debt across services (Bedrock/Vertex adapters, TRPC routers, audit logger) cleared.
  - Queue orchestration emits events, but lifecycle, safety, aggregation, and refinement logic still have TODO-equivalent gaps (missing scoring, judge integration, approval flow persistence).
- **Observability & Ops**
  - OpenTelemetry NodeSDK initialized, yet no instrumentations configured; metrics/exporters optional depending on env vars.
  - No alerting, dashboards, or health checks beyond `/healthz`.
- **Security & Access**
  - JWT-based auth in place; password hashing utilities exist.
  - RBAC enforced in some routers via `assertProjectMembership`, but coverage incomplete (missing auth guards on review/sse routes, etc.).

---

## 2. Alignment vs Specification

| Area | Spec Expectation | Current State | Gap Severity |
| --- | --- | --- | --- |
| **Data Model** | Comprehensive project/experiment/run schema with migrations | Schema defined in `prisma/schema.prisma`, but no migrations/generated client; seed data absent | **Critical** |
| **LLM Integrations** | Multi-provider adapters (OpenAI, Anthropic, Vertex, Bedrock, Azure, Ollama, OpenAI-compatible) with validation, cost modeling | Adapter classes stubbed with partial logic; type errors (Bedrock/Vertex); provider credential rotation + caching incomplete | **Critical** |
| **Experiment Orchestration** | Queue-driven pipeline (execute → judge → aggregate → safety → refine) with SSE updates and budget enforcement | Worker registrations exist but rely on incomplete services (`BudgetEnforcer`, `PromptRefiner`, `SafetyService`). No end-to-end iteration success path proven. | **Critical** |
| **Frontend UX** | App Router dashboard, shadcn/ui components, SSE streaming dashboards, credential management | Skeleton pages + wizard UI only; no interactive TRPC integration verified; SSE client pieces missing; styling baseline only | **High** |
| **Human-in-the-loop** | Review workflows, diff viewer, approvals, audit logs | Review card UI exists, but backend routes partially implemented; audit log service writes but untested; approvals not persisted end-to-end | **High** |
| **Testing** | Vitest unit coverage, Playwright E2E, MSW for mocking | Only targeted Vitest suites for shared schemas & a few services; no integration/E2E tests | **High** |
| **Observability** | Metrics, tracing, structured logs, cost dashboards | Logging exists (Pino); telemetry skeleton but no spans/instrumentations; cost tracking table populated per run but no rollups or dashboards | **Medium** |
| **Security & Compliance** | RBAC, credential vaulting, audit trails, rate limiting, safety guardrails | Some RBAC and audit logging, rate limiter stub; credential encryption/storage strategy unspecified; safety service incomplete | **High** |
| **Docs & Ops** | Deployment guide, environment parity, migration strategy | Docker compose works for local dev; lacking production deployment instructions, migration process, runbooks | **Medium** |

---

## 3. Immediate Blockers

1. **API DTS build gap** – `pnpm --filter @edison/api build` fails at the `.d.ts` phase because `rollup-plugin-dts` lacks Bundler-resolution support; need alternate config (NodeNext build tsconfig, or swap tool) so publish artifacts include typings.
2. **No database migrations applied** – Initial migration exists but automated apply/seed workflow still missing; iteration pipeline will fail once data access begins.
3. **Unfinished orchestration pipeline** – Workers reference services that are incomplete or lack safety checks; inability to complete a single experiment iteration.
4. **Credential/LLM adapter validation** – Need concrete implementations for all providers (handling provider-specific params, error paths, cost estimation, streaming).
5. **Frontend dependency on unimplemented TRPC routes** – UI fetches `run.listByExperiment`, `review.listSuggestions`, etc., but endpoints either stubbed or failing due to upstream gaps.

---

## 4. Phased Delivery Plan

| Phase | Objective | Exit Criteria | Key Deliverables | Status |
| --- | --- | --- | --- | --- |
| **Phase 0 – Foundations** | Make repo buildable & bootable end-to-end | `pnpm -r build` & `pnpm -r test` succeed; migrations generated and applied; Prisma client regenerated; all TypeScript strict errors resolved | Migrations, regenerated Prisma client, type fixes, `diff` typings, Tailwind pipeline finalized | 🚧 In Progress |
| **Phase 1 – Orchestration Core** | Execute a full experiment iteration locally | Background workers complete execute→judge→aggregate→refine pipeline on sample data; SSE stream reflects lifecycle; TRPC endpoints return real data | Fully implemented services (budget, safety, aggregation, refinement), BullMQ flows, deterministic test dataset | ⏳ Not Started |
| **Phase 2 – Frontend Experience** | Deliver spec-compliant dashboard & review UX | Project dashboard lists data, wizard creates experiments, iteration detail page streams updates, review workflow operational | Solid design system (Tailwind + shadcn), SSE client, TRPC hooks, AI-assist components, credential management UI | ⏳ Not Started |
| **Phase 3 – Quality & Compliance** | Harden app for production | Playwright E2E, Vitest coverage on services, audit log verification, rate limiting, security posture, cost monitoring dashboards | Test harnesses, MSW mocks, CI scripts, runbooks, alerting configuration | ⏳ Not Started |
| **Phase 4 – Launch Readiness** | Final polish & documentation | Performance benchmarks hit; production deployment guide; smoke tests under docker compose; release notes | Prod config, migration checklist, telemetry dashboards, documentation suite | ⏳ Not Started |

---

## 5. Near-Term Backlog (Phase 0)

### Data & Tooling
- [x] Author initial Prisma migration set aligned with `prisma/schema.prisma`.
- [x] Run `prisma generate` and commit updated client; ensure `@prisma/client` version matches schema.
- [x] Seed minimal development data (admin user, sample project, dataset, experiment) to unblock UI.
  - [x] Seed script handles missing DB/invalid creds with actionable error and migration reminder.

### Type System Repairs
- [ ] Configure project references so `@edison/shared` resolves without manual path hacks (consider `.d.ts` barrel or package exports). *(In progress via package exports + build pipeline; remaining step: remove root tsconfig path alias once consumer builds stabilise.)*
- [x] Add local `diff` module declarations; eliminate implicit `any` parameters across API & web.
- [x] Update LLM adapter types to satisfy SDK changes (Bedrock `InferenceConfiguration`, Vertex `GenerationConfig`, etc.).
- [x] Define `@edison/shared` package exports so bundlers/builds resolve compiled outputs rather than tsconfig-only aliases.
- [x] Introduce dedicated build configs so `@edison/shared` and `@edison/api` emit TypeScript declarations without relying on tsconfig shortcuts.

### Build & Tooling Hygiene
- [ ] Add `pnpm lint` and `pnpm build` to CI (GitHub Actions or alternative) once builds succeed locally.
- [ ] Document developer setup (prereqs, env vars, seeding) in README.

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| SDK/API churn (Prisma, provider SDKs) | Breaks adapters & type safety | Pin versions, add integration tests, monitor release notes |
| Queue orchestration complexity | Hard-to-debug failures across workers | Add structured event logging, local worker simulator, unit tests per service |
| Data privacy & credential safety | Sensitive model keys stored insecurely | Implement encryption-at-rest (KMS or libsodium), restrict logging, rotate secrets |
| Lack of automated tests | Regression risk | Introduce contract tests (shared schemas), service unit tests, E2E flows |

---

## 7. Decision Log

| Date | Decision | Rationale | Owner |
| --- | --- | --- | --- |
| 2025-10-18 | Tailwind + PostCSS added to web app | Bring frontend in line with spec styling baseline | Codex |
| 2025-10-18 | Authored initial Prisma migration & JSON helper layer | Unblock DB bootstrap and Prisma strict typing across API | Codex |
| 2025-10-18 | Added bundler-aware build config for @edison/shared | Enable shared package declaration output without tsconfig hacks | Codex |
| 2025-10-18 | Added composite unique key & build pipeline for @edison/api declarations | Support deterministic judging upserts and publishable type artifacts | Codex |

_Append new decisions here with timestamps to maintain traceability._

---

## 8. Metrics to Validate Before Launch

- Experiment iteration success rate ≥ 95% over sample suite.
- Judge agreement confidence intervals calculated for each rubric facet.
- SSE latency < 2s p95 during orchestration.
- Cost tracking accuracy within ±2% versus provider billing.
- Playwright regression suite runtime < 10 minutes.

---

## 9. Update Checklist

When a task progresses, update:
1. The relevant checklist item or phase status.
2. Snapshot section if build/test/runtime state changes.
3. Decision log (when applicable).
4. Risks section if new risks appear or mitigations change.

Failure to update this tracker will result in lost context and duplicated effort—treat updates as part of “definition of done.”
