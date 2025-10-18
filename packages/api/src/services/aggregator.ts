import type { Rubric } from '@edison/shared';
import type { PrismaClient } from '@prisma/client';

import type { SafetySummary } from '../lib/events';

import {
  analyzeFacets,
  bootstrapConfidenceIntervals,
  calculateCompositeScores,
  computeCoverageMatrix,
  computePairwiseRanking,
  type AggregatedRun,
  type PairwiseJudgmentInput,
} from './aggregator-math';

export class AggregatorService {
  constructor(private readonly prisma: PrismaClient) {}

  async aggregateIteration(iterationId: string): Promise<{
    compositeScores: Record<string, number>;
    confidenceIntervals: Record<string, { lower: number; upper: number }>;
    pairwiseRanking: ReturnType<typeof computePairwiseRanking>;
    facetAnalysis: Record<string, number>;
    coverageMatrix: ReturnType<typeof computeCoverageMatrix>;
    totalCost: number;
    totalTokens: number;
    compositeScore: number;
    safetySummary?: SafetySummary;
  }> {
    const iteration = await this.prisma.iteration.findUniqueOrThrow({
      where: { id: iterationId },
      include: {
        experiment: true,
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
    const aggregatedRuns: AggregatedRun[] = iteration.modelRuns.map((run) => ({
      id: run.id,
      outputs: run.outputs.map((output) => ({
        tags: output.case.tags,
        difficulty: output.case.difficulty,
        judgments: output.judgments.map((judgment) => ({
          mode: judgment.mode,
          scores: judgment.scores as Record<string, number>,
        })),
      })),
    }));

    const compositeScores = calculateCompositeScores(aggregatedRuns, rubric);
    const confidenceIntervals = bootstrapConfidenceIntervals(aggregatedRuns, rubric, {
      samples: 500,
      seed: iterationId,
    });
    const pairwiseRanking = await this.calculatePairwiseRanking(iterationId);
    const facetAnalysis = analyzeFacets(aggregatedRuns, rubric);
    const coverageMatrix = computeCoverageMatrix(aggregatedRuns, rubric);

    const totalCost = iteration.modelRuns.reduce((sum, run) => sum + run.costUsd, 0);
    const totalTokens = iteration.modelRuns.reduce((sum, run) => sum + run.tokensIn + run.tokensOut, 0);

    const compositeScore = Object.values(compositeScores).reduce((a, b) => a + b, 0) /
      (Object.keys(compositeScores).length || 1);

    const previousMetrics = (iteration.metrics as Record<string, unknown> | null) ?? {};

    await this.prisma.iteration.update({
      where: { id: iterationId },
      data: {
        metrics: {
          ...previousMetrics,
          compositeScores,
          confidenceIntervals,
          pairwiseRanking,
          facetAnalysis,
          coverageMatrix,
          compositeScore,
        },
        totalCost,
        totalTokens,
      },
    });

    return {
      compositeScores,
      confidenceIntervals,
      pairwiseRanking,
      facetAnalysis,
      coverageMatrix,
      totalCost,
      totalTokens,
      compositeScore,
      safetySummary: previousMetrics.safetySummary as SafetySummary | undefined,
    };
  }

  private async calculatePairwiseRanking(
    iterationId: string,
  ): Promise<ReturnType<typeof computePairwiseRanking>> {
    const judgments = await this.prisma.judgment.findMany({
      where: {
        mode: 'PAIRWISE',
        output: {
          modelRun: { iterationId },
        },
      },
      include: {
        output: { include: { modelRun: true } },
        winnerOutput: { include: { modelRun: true } },
      },
    });

    const matches: PairwiseJudgmentInput[] = judgments
      .map((judgment) => {
        const metadata = (judgment.metadata as { competitorModelRunId?: string } | null) ?? {};
        const primaryRunId = judgment.output.modelRunId;
        const competitorRunId = metadata.competitorModelRunId ?? null;
        const winnerRunId = judgment.winnerOutput?.modelRunId ?? null;

        if (!competitorRunId) {
          return null;
        }

        return {
          runIds: [primaryRunId, competitorRunId] as [string, string],
          winnerRunId,
        } satisfies PairwiseJudgmentInput;
      })
      .filter((value): value is PairwiseJudgmentInput => value !== null);

    return computePairwiseRanking(matches);
  }
}
