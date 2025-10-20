import type { StopRules } from '@edison/shared';
import type { PrismaClient } from '@prisma/client';

export class BudgetEnforcer {
  constructor(private readonly prisma: PrismaClient) {}

  async assertWithinBudget(experimentId: string): Promise<void> {
    const experiment = await this.prisma.experiment.findUniqueOrThrow({
      where: { id: experimentId },
    });

    const stopRules = ((experiment.stopRules as StopRules | null) ?? {}) as StopRules;

    if (!stopRules.maxBudgetUsd && !stopRules.maxTotalTokens) {
      return;
    }

    const totals = await this.prisma.iteration.aggregate({
      where: { experimentId },
      _sum: {
        totalCost: true,
        totalTokens: true,
      },
    });

    if (stopRules.maxBudgetUsd && (totals._sum.totalCost ?? 0) >= stopRules.maxBudgetUsd) {
      throw new Error('Experiment budget exhausted');
    }

    if (stopRules.maxTotalTokens && (totals._sum.totalTokens ?? 0) >= stopRules.maxTotalTokens) {
      throw new Error('Token budget exhausted');
    }
  }

  async estimateIterationCost(experimentId: string, promptVersionId: string): Promise<number> {
    const [promptVersion, experiment] = await Promise.all([
      this.prisma.promptVersion.findUniqueOrThrow({ where: { id: promptVersionId } }),
      this.prisma.experiment.findUniqueOrThrow({
        where: { id: experimentId },
        include: {
          modelConfigs: { where: { isActive: true } },
          project: { include: { datasets: true } },
        },
      }),
    ]);

    const datasetIds = this.resolveDatasetIds(
      experiment.project.datasets.map(({ id }) => id),
      experiment.selectorConfig,
    );

    const datasets = await this.prisma.dataset.findMany({
      where: { projectId: experiment.projectId, id: { in: datasetIds } },
      include: { cases: true },
    });

    if (datasets.length !== datasetIds.length) {
      throw new Error('Experiment references datasets that do not exist in the project');
    }

    const promptLength = promptVersion.text.length + (promptVersion.systemText?.length ?? 0);
    const tokensPerCase = Math.ceil(promptLength / 4);
    const totalCases = datasets.reduce<number>((sum, dataset) => sum + dataset.cases.length, 0) || 1;
    const models = experiment.modelConfigs.length || 1;

    const estimatedTokens = tokensPerCase * totalCases * models * 2; // prompt + completion

    const stopRules = ((experiment.stopRules as StopRules | null) ?? {}) as StopRules;

    if (stopRules.maxTotalTokens && estimatedTokens > stopRules.maxTotalTokens) {
      throw new Error('Estimated iteration tokens exceed configured maximum');
    }

    return estimatedTokens;
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

  async getBudgetStatus(
    experimentId: string,
  ): Promise<{
    totalCost: number;
    totalTokens: number;
    budgetLimitUsd?: number;
    tokenLimit?: number;
    percentBudgetUsed?: number;
    percentTokenUsed?: number;
  }> {
    const experiment = await this.prisma.experiment.findUniqueOrThrow({ where: { id: experimentId } });
    const stopRules = (experiment.stopRules as StopRules | null) ?? ({} as StopRules);

    const totals = await this.prisma.iteration.aggregate({
      where: { experimentId },
      _sum: { totalCost: true, totalTokens: true },
    });

    const totalCost = totals._sum.totalCost ?? 0;
    const totalTokens = totals._sum.totalTokens ?? 0;
    const budgetLimitUsd = stopRules.maxBudgetUsd;
    const tokenLimit = stopRules.maxTotalTokens;

    return {
      totalCost,
      totalTokens,
      budgetLimitUsd,
      tokenLimit,
      percentBudgetUsed: budgetLimitUsd ? Math.min(totalCost / budgetLimitUsd, 1) : undefined,
      percentTokenUsed: tokenLimit ? Math.min(totalTokens / tokenLimit, 1) : undefined,
    };
  }
}
