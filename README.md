# Edison - Automated prompt engineering
Edison systematically evolves your prompts through automated testing across multiple LLMs, aggregated AI judge evaluation, and guided iterative refinement—with human-in-the-loop validation at every step.

## Monorepo structure

- `packages/shared` – Shared Zod schemas and types for validation and prompt metadata.
- `packages/api` – Hono + tRPC API server with Prisma persistence, BullMQ orchestration, LLM adapters, and refinement workers.
- `apps/web` – Next.js 14 interface with experiment wizard primitives and project overview screens.
- `prisma` – Database schema mirroring the Edison v1 specification.

## Getting started

### Option 1: Docker (Recommended)

The easiest way to run Edison with all dependencies:

```bash
# Copy environment template
cp .env.docker.example .env

# Edit .env and add your API keys
# At minimum set: OPENAI_API_KEY, ANTHROPIC_API_KEY

# Start all services (PostgreSQL, Redis, API, Web)
docker-compose up
```

Access the application at [http://localhost:3000](http://localhost:3000)

For detailed Docker documentation, see [README.docker.md](./README.docker.md)

### Option 2: Local Development

Requirements: Node.js 22+, PostgreSQL 18+, Redis 7.4+, pnpm 10+

```bash
pnpm install

# Run database migrations
pnpm --filter @edison/api prisma migrate deploy

# Start the API (registers workers automatically)
pnpm --filter @edison/api dev

# In another terminal start the web application
pnpm dev
```

Configure environment variables by copying `.env.example` to `.env.local` (for the API) and `.env.local` inside `apps/web` as needed. At minimum provide `DATABASE_URL`, `REDIS_URL`, API credentials, `JWT_SECRET`, `ENCRYPTION_KEY`, and `API_BASE_URL`/`NEXT_PUBLIC_API_URL` for the web proxy.
