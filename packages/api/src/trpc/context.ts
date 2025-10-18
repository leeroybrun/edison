import { randomUUID } from 'crypto';

import type { PrismaClient } from '@prisma/client';
import type { inferAsyncReturnType } from '@trpc/server';
import { initTRPC, TRPCError } from '@trpc/server';
import type { HonoContext } from 'hono';
import superjson from 'superjson';

import { authenticate } from '../lib/auth';
import type { LLMAdapterFactory } from '../llm/factory';
import type { EdisonQueues } from '../queue/queues';
import type { AIAssistService } from '../services/ai-assist';
import type { GeneratorService } from '../services/generator';
import type { IterationOrchestrator } from '../services/orchestrator';

export interface ContextDependencies {
  prisma: PrismaClient;
  queues: EdisonQueues;
  orchestrator: IterationOrchestrator;
  adapterFactory: LLMAdapterFactory;
  aiAssist: AIAssistService;
  generator: GeneratorService;
}

export function createContextFactory(deps: ContextDependencies) {
  return async function createContext(ctx: HonoContext) {
    const user = await authenticate(ctx.req.header('authorization'));
    return {
      user,
      prisma: deps.prisma,
      queues: deps.queues,
      orchestrator: deps.orchestrator,
      adapterFactory: deps.adapterFactory,
      aiAssist: deps.aiAssist,
      generator: deps.generator,
      requestId: randomUUID(),
    };
  };
}

export type Context = inferAsyncReturnType<ReturnType<typeof createContextFactory>>;

const t = initTRPC.context<Context>().create({
  transformer: superjson,
});

export const router = t.router;
export const publicProcedure = t.procedure;
export const protectedProcedure = t.procedure.use(async ({ ctx, next }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }
  return next({ ctx });
});
