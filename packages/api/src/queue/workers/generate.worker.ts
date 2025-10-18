import { SpanStatusCode, trace } from '@opentelemetry/api';
import { Worker } from 'bullmq';

import { logger } from '../../lib/logger';
import { prisma } from '../../lib/prisma';
import { redis } from '../../lib/redis';
import { LLMAdapterFactory } from '../../llm/factory';
import { GeneratorService } from '../../services/generator';

const adapterFactory = new LLMAdapterFactory(prisma);
const generator = new GeneratorService(prisma, adapterFactory);
const tracer = trace.getTracer('edison.worker.generate');

export function registerGenerateWorker(): Worker {
  const worker = new Worker(
    'generate-dataset',
    async (job) => {
      const { datasetId, projectId, spec } = job.data as {
        datasetId: string;
        projectId: string;
        spec: { count: number; diversity: number; domainHints: string };
      };

      return tracer.startActiveSpan('GenerateWorker.generate', async (span) => {
        try {
          await generator.generateSyntheticDataset(projectId, spec, datasetId);
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
    { connection: redis, concurrency: 1 },
  );

  worker.on('failed', (job, err) => {
    logger.error({ jobId: job?.id, err }, 'generate worker failed');
  });

  return worker;
}
