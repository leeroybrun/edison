import { serve } from '@hono/node-server';
import { Hono } from 'hono';

import { getConfig } from './lib/config';
import { LockManager } from './lib/locks';
import { logger } from './lib/logger';
import { prisma } from './lib/prisma';
import { redis } from './lib/redis';
import { initTelemetry } from './lib/telemetry';
import { LLMAdapterFactory } from './llm/factory';
import { createQueues } from './queue/queues';
import { registerAggregateWorker } from './queue/workers/aggregate.worker';
import { registerExecuteWorker } from './queue/workers/execute.worker';
import { registerGenerateWorker } from './queue/workers/generate.worker';
import { registerJudgeWorker } from './queue/workers/judge.worker';
import { registerRefineWorker } from './queue/workers/refine.worker';
import { registerSafetyWorker } from './queue/workers/safety.worker';
import { AIAssistService } from './services/ai-assist';
import { AuditLogger } from './services/audit-logger';
import { BudgetEnforcer } from './services/budget-enforcer';
import { GeneratorService } from './services/generator';
import { IterationOrchestrator } from './services/orchestrator';
import { RateLimiter } from './services/rate-limiter';
import { createIterationStreamHandler } from './sse/iteration-stream';
import { createTRPCMiddleware } from './trpc/router';
const config = getConfig();
initTelemetry();
const queues = createQueues(redis);
const budgetEnforcer = new BudgetEnforcer(prisma);
const lockManager = new LockManager(redis);
const orchestrator = new IterationOrchestrator(prisma, queues, budgetEnforcer, lockManager);
const adapterFactory = new LLMAdapterFactory(prisma);
const generatorService = new GeneratorService(prisma, adapterFactory);
const aiAssistService = new AIAssistService(adapterFactory);
const auditLogger = new AuditLogger(prisma);
const rateLimiter = new RateLimiter(redis);

registerExecuteWorker(orchestrator);
registerJudgeWorker(orchestrator);
registerAggregateWorker(orchestrator);
registerRefineWorker(orchestrator);
registerGenerateWorker();
registerSafetyWorker(orchestrator);

const app = new Hono();
app.get('/healthz', (c) => c.json({ status: 'ok' }));

app.route(
  '/trpc',
  createTRPCMiddleware({
    prisma,
    queues,
    orchestrator,
    adapterFactory,
    aiAssist: aiAssistService,
    generator: generatorService,
    auditLogger,
    rateLimiter,
  }),
);
app.get('/iterations/:id/stream', createIterationStreamHandler(prisma));

export function startServer(): void {
  serve({ fetch: app.fetch, port: config.PORT });
  logger.info({ port: config.PORT }, 'API server listening');
}

if (process.env.NODE_ENV !== 'test') {
  startServer();
}
