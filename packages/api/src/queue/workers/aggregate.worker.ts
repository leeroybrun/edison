import { SpanStatusCode, trace } from '@opentelemetry/api';
import { Worker } from 'bullmq';

import { logger } from '../../lib/logger';
import { prisma } from '../../lib/prisma';
import { redis } from '../../lib/redis';
import { AggregatorService } from '../../services/aggregator';
import type { IterationOrchestrator } from '../../services/orchestrator';

const aggregator = new AggregatorService(prisma);
const tracer = trace.getTracer('edison.worker.aggregate');

export function registerAggregateWorker(orchestrator: IterationOrchestrator): Worker {
  const worker = new Worker(
    'aggregate-iteration',
    async (job) => {
      const { iterationId } = job.data as { iterationId: string };
      return tracer.startActiveSpan('AggregateWorker.aggregate', async (span) => {
        try {
          const metrics = await aggregator.aggregateIteration(iterationId);
          await orchestrator.handleAggregationComplete(iterationId, metrics);
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
    { connection: redis },
  );

  worker.on('failed', (job, err) => {
    logger.error({ jobId: job?.id, err }, 'aggregate worker failed');
  });

  return worker;
}
