import { FewShotExampleSchema, type Rubric } from '@edison/shared';
import { SpanStatusCode, trace } from '@opentelemetry/api';
import { Worker } from 'bullmq';

import { logger } from '../../lib/logger';
import { prisma } from '../../lib/prisma';
import { redis } from '../../lib/redis';
import { LLMAdapterFactory } from '../../llm/factory';
import type { IterationOrchestrator } from '../../services/orchestrator';
import { PromptRefiner } from '../../services/prompt-refiner';

const adapterFactory = new LLMAdapterFactory(prisma);
const promptRefiner = new PromptRefiner();
const tracer = trace.getTracer('edison.worker.refine');

export function registerRefineWorker(orchestrator: IterationOrchestrator): Worker {
  const worker = new Worker(
    'refine-prompt',
    async (job) => {
      const { iterationId } = job.data as { iterationId: string };
      return tracer.startActiveSpan('RefineWorker.refine', async (span) => {
        try {
          const iteration = await prisma.iteration.findUniqueOrThrow({
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

          const rubric = iteration.experiment.rubric as Rubric;
          const weakDiagnostics = JSON.stringify(iteration.metrics ?? {}, null, 2);

          const credential = await adapterFactory.getCredentialForProject(iteration.experiment.projectId, 'OPENAI');
          const adapter = await adapterFactory.getAdapter(credential, 'gpt-4o');
          const fewShots = iteration.promptVersion.fewShots
            ? FewShotExampleSchema.array().parse(iteration.promptVersion.fewShots)
            : undefined;
          const result = await promptRefiner.refine({
            goal: iteration.experiment.goal,
            rubric,
            prompt: {
              name: `Prompt v${iteration.promptVersion.version}`,
              text: iteration.promptVersion.text,
              systemText: iteration.promptVersion.systemText ?? undefined,
              fewShots,
              toolsSchema: iteration.promptVersion.toolsSchema ?? undefined,
            },
            adapter,
            diagnostics: weakDiagnostics,
          });

          const suggestion = await prisma.suggestion.create({
            data: {
              promptVersionId: iteration.promptVersionId,
              source: 'refiner_llm',
              diffUnified: result.diff,
              note: result.note,
              targetCriteria: rubric.map((criterion) => criterion.name),
              status: 'PENDING',
            },
          });

          await orchestrator.handleRefinementComplete(iterationId, suggestion.id);
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
    logger.error({ jobId: job?.id, err }, 'refine worker failed');
  });

  return worker;
}
