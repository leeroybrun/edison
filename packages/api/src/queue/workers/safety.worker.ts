import { SpanStatusCode, trace } from '@opentelemetry/api';
import { Worker } from 'bullmq';

import { logger } from '../../lib/logger';
import { prisma } from '../../lib/prisma';
import { redis } from '../../lib/redis';
import type { IterationOrchestrator } from '../../services/orchestrator';
import { SafetyService } from '../../services/safety';

const safetyService = new SafetyService(prisma);
const tracer = trace.getTracer('edison.worker.safety');

export function registerSafetyWorker(orchestrator: IterationOrchestrator): Worker {
  const worker = new Worker(
    'safety-scan',
    async (job) => {
      const { iterationId } = job.data as { iterationId: string };
      return tracer.startActiveSpan('SafetyWorker.scan', async (span) => {
        try {
          const summary = await safetyService.scanIteration(iterationId);
          await orchestrator.handleSafetyComplete(iterationId, summary);
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
    logger.error({ jobId: job?.id, err }, 'safety worker failed');
  });

  return worker;
}
