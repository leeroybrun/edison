import { DatasetCaseSchema, ModelParamsSchema } from '@edison/shared';
import { SpanStatusCode, trace } from '@opentelemetry/api';
import { Worker, type Job } from 'bullmq';

import { appEvents } from '../../lib/events';
import { logger } from '../../lib/logger';
import { prisma } from '../../lib/prisma';
import { redis } from '../../lib/redis';
import { LLMAdapterFactory } from '../../llm/factory';
import { asNullableJson } from '../../lib/json';
import type { IterationOrchestrator } from '../../services/orchestrator';

const adapterFactory = new LLMAdapterFactory(prisma);
const tracer = trace.getTracer('edison.worker.execute');

export function registerExecuteWorker(orchestrator: IterationOrchestrator): Worker {
  const worker = new Worker(
    'execute-run',
    async (job: Job) => {
      const { modelRunId } = job.data as { modelRunId: string };

      await prisma.modelRun.update({
        where: { id: modelRunId },
        data: { status: 'RUNNING', startedAt: new Date() },
      });

      return tracer.startActiveSpan('ExecuteWorker.run', async (span) => {
        try {
          const modelRun = await prisma.modelRun.findUniqueOrThrow({
            where: { id: modelRunId },
            include: {
              promptVersion: true,
              modelConfig: true,
              iteration: {
                include: {
                  experiment: {
                    include: {
                      project: {
                        include: {
                          providers: true,
                        },
                      },
                    },
                  },
                },
              },
            },
          });

          const datasetCases = await prisma.case.findMany({
            where: { datasetId: modelRun.datasetId },
          });

          if (datasetCases.length === 0) {
            await prisma.modelRun.update({
              where: { id: modelRunId },
              data: {
                status: 'COMPLETED',
                finishedAt: new Date(),
              },
            });
            appEvents.emit('modelRun:completed', { iterationId: modelRun.iterationId });
            span.setStatus({ code: SpanStatusCode.OK });
            return;
          }

          const credential = modelRun.iteration.experiment.project.providers.find(
            (p) => p.provider === modelRun.modelConfig.provider && p.isActive,
          );

          if (!credential) {
            throw new Error('Provider credential not found for run');
          }

          const adapter = await adapterFactory.getAdapter(credential, modelRun.modelConfig.modelId);

          let totalTokensIn = 0;
          let totalTokensOut = 0;
          let totalCost = 0;
          const params = ModelParamsSchema.partial().parse(
            modelRun.modelConfig.params ?? {},
          );

          for (const [index, testCase] of datasetCases.entries()) {
            const inputVariables = DatasetCaseSchema.shape.input.parse(testCase.input);
            const renderedPrompt = renderPrompt(modelRun.promptVersion.text, inputVariables);
            const messages: { role: 'system' | 'user'; content: string }[] = [];
            if (modelRun.promptVersion.systemText) {
              messages.push({ role: 'system', content: modelRun.promptVersion.systemText });
            }
            messages.push({ role: 'user', content: renderedPrompt });

            const response = await adapter.chat(messages, {
              params,
              seed: modelRun.modelConfig.seed ?? undefined,
            });

            await prisma.output.create({
              data: {
                modelRunId,
                caseId: testCase.id,
                rawText: response.text,
                parsed: asNullableJson(null),
                tokensOut: response.usage.completionTokens,
                latencyMs: response.latencyMs,
                cached: response.cached,
              },
            });

            totalTokensIn += response.usage.promptTokens;
            totalTokensOut += response.usage.completionTokens;
            totalCost += adapter.estimateCost(response.usage.promptTokens, response.usage.completionTokens);

            await job.updateProgress({ completed: index + 1, total: datasetCases.length });
          }

          await prisma.modelRun.update({
            where: { id: modelRunId },
            data: {
              status: 'COMPLETED',
              tokensIn: totalTokensIn,
              tokensOut: totalTokensOut,
              costUsd: totalCost,
              finishedAt: new Date(),
            },
          });

          await prisma.costTracking.create({
            data: {
              projectId: modelRun.iteration.experiment.projectId,
              provider: modelRun.modelConfig.provider,
              modelId: modelRun.modelConfig.modelId,
              tokensIn: totalTokensIn,
              tokensOut: totalTokensOut,
              costUsd: totalCost,
            },
          });

          appEvents.emit('modelRun:completed', { iterationId: modelRun.iterationId });
          span.setStatus({ code: SpanStatusCode.OK });
        } catch (error) {
          logger.error({ err: error, modelRunId }, 'execute-run failed');
          const run = await prisma.modelRun.findUnique({ where: { id: modelRunId } });

          if (run) {
            await prisma.modelRun.update({
              where: { id: modelRunId },
              data: {
                status: 'FAILED',
                errorMessage: error instanceof Error ? error.message : 'Unknown error',
                finishedAt: new Date(),
              },
            });

            appEvents.emit('modelRun:failed', {
              iterationId: run.iterationId,
              error: error instanceof Error ? error.message : 'Unknown error',
            });
          }

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
    { connection: redis, concurrency: 5 },
  );

  worker.on('completed', (job) => {
    logger.debug({ jobId: job.id }, 'execute worker completed job');
  });

  worker.on('failed', (job, err) => {
    logger.error({ jobId: job?.id, err }, 'execute worker failed job');
  });

  appEvents.on('modelRun:completed', ({ iterationId }) => {
    void orchestrator.handleRunProgress(iterationId);
  });

  appEvents.on('modelRun:failed', ({ iterationId, error }) => {
    void orchestrator.handleRunProgress(iterationId, error);
  });

  return worker;
}

function renderPrompt(template: string, variables: Record<string, unknown>): string {
  return Object.entries(variables).reduce((acc, [key, value]) => {
    return acc.replace(new RegExp(`{{\\s*${key}\\s*}}`, 'g'), String(value));
  }, template);
}
