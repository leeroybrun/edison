import { randomUUID } from 'crypto';

import type { PrismaClient } from '@prisma/client';
import type { inferAsyncReturnType } from '@trpc/server';
import { initTRPC, TRPCError } from '@trpc/server';
import type { Context as HonoContext } from 'hono';
import superjson from 'superjson';

import { authenticate } from '../lib/auth';
import { isAppError } from '../lib/errors';
import type { LLMAdapterFactory } from '../llm/factory';
import type { EdisonQueues } from '../queue/queues';
import type { AIAssistService } from '../services/ai-assist';
import type { AuditLogger } from '../services/audit-logger';
import type { GeneratorService } from '../services/generator';
import type { IterationOrchestrator } from '../services/orchestrator';
import type { RateLimiter } from '../services/rate-limiter';

export interface ContextDependencies {
  prisma: PrismaClient;
  queues: EdisonQueues;
  orchestrator: IterationOrchestrator;
  adapterFactory: LLMAdapterFactory;
  aiAssist: AIAssistService;
  generator: GeneratorService;
  auditLogger: AuditLogger;
  rateLimiter: RateLimiter;
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
      auditLogger: deps.auditLogger,
      rateLimiter: deps.rateLimiter,
      requestId: randomUUID(),
    };
  };
}

export type Context = inferAsyncReturnType<ReturnType<typeof createContextFactory>>;

const t = initTRPC.context<Context>().create({
  transformer: superjson,
});

type TrpcErrorCode =
  | 'BAD_REQUEST'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'TOO_MANY_REQUESTS'
  | 'INTERNAL_SERVER_ERROR';

const appErrorMiddleware = t.middleware(async ({ next }) => {
  try {
    return await next();
  } catch (error) {
    if (isAppError(error)) {
      const statusMap: Record<number, TrpcErrorCode> = {
        400: 'BAD_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        409: 'CONFLICT',
        422: 'BAD_REQUEST',
        429: 'TOO_MANY_REQUESTS',
        503: 'INTERNAL_SERVER_ERROR',
      } as const;

      const code = statusMap[(error as { status: number }).status] ?? 'INTERNAL_SERVER_ERROR';
      throw new TRPCError({ code, message: (error as Error).message });
    }
    throw error;
  }
});

export const router = t.router;
export const publicProcedure = t.procedure.use(appErrorMiddleware);
export const protectedProcedure = publicProcedure.use(async ({ ctx, next }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }
  return next({ ctx });
});
