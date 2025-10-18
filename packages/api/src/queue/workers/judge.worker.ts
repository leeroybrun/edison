import { SpanStatusCode, trace } from '@opentelemetry/api';
import { Worker } from 'bullmq';

import { logger } from '../../lib/logger';
import { prisma } from '../../lib/prisma';
import { redis } from '../../lib/redis';
import { LLMAdapterFactory } from '../../llm/factory';
import { EvaluatorService } from '../../services/evaluator';
import type { IterationOrchestrator } from '../../services/orchestrator';

const adapterFactory = new LLMAdapterFactory(prisma);
const evaluator = new EvaluatorService(prisma, adapterFactory);
const tracer = trace.getTracer('edison.worker.judge');

export function registerJudgeWorker(orchestrator: IterationOrchestrator): Worker {
  const worker = new Worker(
    'judge-outputs',
    async (job) => {
      const { iterationId } = job.data as { iterationId: string };
      return tracer.startActiveSpan('JudgeWorker.judge', async (span) => {
        try {
          await evaluator.judgeIteration(iterationId);
          await orchestrator.handleJudgingComplete(iterationId);
          span.setStatus({ code: SpanStatusCode.OK });
        } catch (error) {
          if (error instanceof Error) {
            span.recordException(error);
            span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
          }
          throw error;
        } finally {
          span.end();
        }
      });
    },
    { connection: redis, concurrency: 2 },
  );

  worker.on('failed', (job, err) => {
    logger.error({ jobId: job?.id, err }, 'judge worker failed');
  });

  return worker;
}
