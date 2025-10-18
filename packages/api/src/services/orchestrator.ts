import { SpanStatusCode, trace } from '@opentelemetry/api';
import type { PrismaClient } from '@prisma/client';

import { appEvents, type IterationMetricsPayload, type SafetySummary } from '../lib/events';
import { logger } from '../lib/logger';
import type { EdisonQueues } from '../queue/queues';

import { BudgetEnforcer } from './budget-enforcer';

export class IterationOrchestrator {
  private readonly tracer = trace.getTracer('edison.orchestrator');

  constructor(
    private readonly prisma: PrismaClient,
    private readonly queues: EdisonQueues,
    private readonly budgetEnforcer: BudgetEnforcer,
  ) {}

  async startIteration(experimentId: string, promptVersionId: string): Promise<string> {
    return this.tracer.startActiveSpan('IterationOrchestrator.startIteration', async (span) => {
      try {
        await this.budgetEnforcer.assertWithinBudget(experimentId);
        await this.budgetEnforcer.estimateIterationCost(experimentId, promptVersionId);

        const experiment = await this.prisma.experiment.findUniqueOrThrow({
          where: { id: experimentId },
          include: {
            modelConfigs: { where: { isActive: true } },
            project: { include: { datasets: true } },
          },
        });

        if (experiment.modelConfigs.length === 0) {
          throw new Error('Experiment requires at least one active model configuration');
        }

        const datasetIds = this.resolveDatasetIds(
          experiment.project.datasets.map((dataset) => dataset.id),
          experiment.selectorConfig,
        );
        if (datasetIds.length === 0) {
          throw new Error('Experiment requires at least one dataset');
        }

        const datasets = await this.prisma.dataset.findMany({
          where: { id: { in: datasetIds }, projectId: experiment.projectId },
          select: { id: true },
        });

        if (datasets.length !== datasetIds.length) {
          throw new Error('Experiment references datasets that do not exist in the project');
        }

        const lastIteration = await this.prisma.iteration.findFirst({
          where: { experimentId },
          orderBy: { number: 'desc' },
        });

        const iteration = await this.prisma.iteration.create({
          data: {
            experimentId,
            promptVersionId,
            number: (lastIteration?.number ?? 0) + 1,
            status: 'EXECUTING',
            startedAt: new Date(),
          },
        });

        const totalRuns = experiment.modelConfigs.length * datasets.length;

        for (const modelConfig of experiment.modelConfigs) {
          for (const dataset of datasets) {
            const run = await this.prisma.modelRun.create({
              data: {
                iterationId: iteration.id,
                promptVersionId,
                modelConfigId: modelConfig.id,
                datasetId: dataset.id,
                status: 'PENDING',
              },
            });

            await this.queues.execute.add('execute-run', { iterationId: iteration.id, modelRunId: run.id });
          }
        }

        appEvents.emit('iteration:event', {
          iterationId: iteration.id,
          type: 'status',
          payload: { status: 'EXECUTING' },
        });
        appEvents.emit('iteration:event', {
          iterationId: iteration.id,
          type: 'run-progress',
          payload: { completedRuns: 0, totalRuns, failedRuns: 0 },
        });

        logger.info({ iterationId: iteration.id }, 'iteration started');
        span.setStatus({ code: SpanStatusCode.OK });
        return iteration.id;
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
  }

  async handleRunProgress(iterationId: string, failureMessage?: string): Promise<void> {
    const span = this.tracer.startSpan('IterationOrchestrator.handleRunProgress');
    try {
      const runs = await this.prisma.modelRun.findMany({ where: { iterationId } });
      const totalRuns = runs.length;
      const completedRuns = runs.filter((run) => run.status === 'COMPLETED').length;
      const failedRuns = runs.filter((run) => run.status === 'FAILED').length;
      const anyFailed = failedRuns > 0;
      const allCompleted =
        completedRuns + failedRuns === totalRuns && totalRuns > 0 && !runs.some((run) => run.status === 'RUNNING');

      appEvents.emit('iteration:event', {
        iterationId,
        type: 'run-progress',
        payload: { completedRuns, totalRuns, failedRuns },
      });

      if (anyFailed) {
        await this.prisma.iteration.update({
          where: { id: iterationId },
          data: { status: 'FAILED', finishedAt: new Date() },
        });
        const message = failureMessage ?? 'Run failed. Inspect the job logs for details.';
        appEvents.emit('iteration:event', {
          iterationId,
          type: 'status',
          payload: { status: 'FAILED' },
        });
        appEvents.emit('iteration:event', {
          iterationId,
          type: 'failure',
          payload: { message },
        });
        logger.error({ iterationId, message }, 'iteration failed due to run error');
        span.setStatus({ code: SpanStatusCode.ERROR, message });
        return;
      }

      if (!allCompleted) {
        span.setStatus({ code: SpanStatusCode.OK });
        return;
      }

      await this.queues.safety.add('safety-scan', { iterationId });
      appEvents.emit('iteration:event', {
        iterationId,
        type: 'status',
        payload: { status: 'SAFETY_CHECKING' },
      });
      logger.info({ iterationId }, 'all runs completed; queued safety scan');
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
  }

  async handleJudgingComplete(iterationId: string): Promise<void> {
    await this.prisma.iteration.update({ where: { id: iterationId }, data: { status: 'AGGREGATING' } });

    const totalOutputs = await this.prisma.output.count({
      where: {
        modelRun: { iterationId },
      },
    });

    appEvents.emit('iteration:event', {
      iterationId,
      type: 'status',
      payload: { status: 'AGGREGATING' },
    });
    appEvents.emit('iteration:event', {
      iterationId,
      type: 'judging-complete',
      payload: { totalOutputs },
    });

    await this.queues.aggregate.add('aggregate-iteration', { iterationId });
    logger.info({ iterationId }, 'judging complete; queued aggregation');
  }

  async handleAggregationComplete(iterationId: string, metrics: IterationMetricsPayload): Promise<void> {
    await this.prisma.iteration.update({ where: { id: iterationId }, data: { status: 'REFINING' } });

    appEvents.emit('iteration:event', {
      iterationId,
      type: 'status',
      payload: { status: 'REFINING' },
    });
    appEvents.emit('iteration:event', {
      iterationId,
      type: 'metrics',
      payload: metrics,
    });

    await this.queues.refine.add('refine-prompt', { iterationId });
    logger.info({ iterationId }, 'aggregation complete; queued refinement');
  }

  async handleRefinementComplete(iterationId: string, suggestionId: string | null): Promise<void> {
    const iteration = await this.prisma.iteration.findUniqueOrThrow({
      where: { id: iterationId },
      select: { metrics: true },
    });

    await this.prisma.iteration.update({
      where: { id: iterationId },
      data: {
        status: 'REVIEWING',
        finishedAt: new Date(),
        metrics: { ...(iteration.metrics as Record<string, unknown> | null ?? {}), latestSuggestionId: suggestionId },
      },
    });

    appEvents.emit('iteration:event', {
      iterationId,
      type: 'status',
      payload: { status: 'REVIEWING' },
    });
    appEvents.emit('iteration:event', {
      iterationId,
      type: 'refinement',
      payload: { suggestionId },
    });

    logger.info({ iterationId, suggestionId }, 'refinement complete; awaiting review');
  }

  async handleSafetyComplete(iterationId: string, summary: SafetySummary): Promise<void> {
    const span = this.tracer.startSpan('IterationOrchestrator.handleSafetyComplete');
    try {
      await this.prisma.iteration.update({ where: { id: iterationId }, data: { status: 'JUDGING' } });

      appEvents.emit('iteration:event', {
        iterationId,
        type: 'status',
        payload: { status: 'JUDGING' },
      });
      appEvents.emit('iteration:event', {
        iterationId,
        type: 'safety',
        payload: summary,
      });

      await this.queues.judge.add('judge-outputs', { iterationId });
      logger.info({ iterationId }, 'safety scan completed; queued judging');
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
  }

  private resolveDatasetIds(defaultDatasetIds: string[], selectorConfig: unknown): string[] {
    const parsed = (typeof selectorConfig === 'object' && selectorConfig !== null
      ? (selectorConfig as { datasetIds?: unknown })
      : {}) ?? {};

    const explicit = Array.isArray(parsed.datasetIds)
      ? parsed.datasetIds.filter((value): value is string => typeof value === 'string')
      : [];

    if (explicit.length > 0) {
      return Array.from(new Set(explicit));
    }

    return Array.from(new Set(defaultDatasetIds));
  }
}
