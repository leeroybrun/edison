import type { Rubric, RubricCriterion } from '@edison/shared';
import seedrandom from 'seedrandom';

type JudgmentMode = 'POINTWISE' | 'PAIRWISE';

export interface AggregatedJudgment {
  mode: JudgmentMode;
  scores: Record<string, number>;
}

export interface AggregatedOutput {
  tags: string[];
  judgments: AggregatedJudgment[];
  difficulty: number | null;
}

export interface AggregatedRun {
  id: string;
  outputs: AggregatedOutput[];
}

export function calculateCompositeScores(runs: AggregatedRun[], rubric: Rubric): Record<string, number> {
  const weights = buildWeightMap(rubric);
  const totals: Record<string, number> = {};

  for (const run of runs) {
    const pointwise = run.outputs.flatMap((output) =>
      output.judgments.filter((judgment) => judgment.mode === 'POINTWISE'),
    );

    if (pointwise.length === 0) {
      totals[run.id] = 0;
      continue;
    }

    const composites = pointwise.map((judgment) =>
      Object.entries(judgment.scores).reduce((acc, [criterion, value]) => {
        const weight = weights[criterion] ?? 0;
        const numeric = toFiniteNumber(value);
        return acc + numeric * weight;
      }, 0),
    );

    const sum = composites.reduce((acc, value) => acc + value, 0);
    totals[run.id] = sum / composites.length;
  }

  return totals;
}

export function bootstrapConfidenceIntervals(
  runs: AggregatedRun[],
  rubric: Rubric,
  options: { samples?: number; seed?: string } = {},
): Record<string, { lower: number; upper: number }> {
  const { samples = 500, seed = 'edison-bootstrap' } = options;
  const weights = buildWeightMap(rubric);
  const intervals: Record<string, { lower: number; upper: number }> = {};

  for (const run of runs) {
    const pointwise = run.outputs.flatMap((output) =>
      output.judgments.filter((judgment) => judgment.mode === 'POINTWISE'),
    );

    if (pointwise.length === 0) {
      intervals[run.id] = { lower: 0, upper: 0 };
      continue;
    }

    const composites = pointwise.map((judgment) =>
      Object.entries(judgment.scores).reduce((acc, [criterion, value]) => {
        const weight = weights[criterion] ?? 0;
        const numeric = toFiniteNumber(value);
        return acc + weight * numeric;
      }, 0),
    );

    const rng = seedrandom(`${seed}:${run.id}`);
    const bootstrap: number[] = [];

    for (let i = 0; i < samples; i += 1) {
      let subtotal = 0;
      for (let j = 0; j < composites.length; j += 1) {
        const index = Math.floor(rng() * composites.length);
        subtotal += composites[index];
      }
      bootstrap.push(subtotal / composites.length);
    }

    bootstrap.sort((a, b) => a - b);
    const lowerIndex = Math.floor(0.025 * bootstrap.length);
    const upperIndex = Math.ceil(0.975 * bootstrap.length) - 1;

    intervals[run.id] = {
      lower: bootstrap[Math.max(0, Math.min(lowerIndex, bootstrap.length - 1))],
      upper: bootstrap[Math.max(0, Math.min(upperIndex, bootstrap.length - 1))],
    };
  }

  return intervals;
}

export function analyzeFacets(runs: AggregatedRun[], rubric: Rubric): Record<string, number> {
  const weights = buildWeightMap(rubric);
  const totals: Record<string, { sum: number; count: number }> = {};

  for (const run of runs) {
    for (const output of run.outputs) {
      const pointwise = output.judgments.filter((judgment) => judgment.mode === 'POINTWISE');
      if (pointwise.length === 0) {
        continue;
      }

      const composite = pointwise.reduce((acc, judgment) => {
        const score = Object.entries(judgment.scores).reduce((subtotal, [criterion, value]) => {
          const weight = weights[criterion] ?? 0;
          const numeric = toFiniteNumber(value);
          return subtotal + weight * numeric;
        }, 0);
        return acc + score;
      }, 0) / pointwise.length;

      for (const tag of output.tags) {
        const bucket = totals[tag] ?? { sum: 0, count: 0 };
        bucket.sum += composite;
        bucket.count += 1;
        totals[tag] = bucket;
      }
    }
  }

  return Object.fromEntries(
    Object.entries(totals).map(([tag, value]) => [tag, value.count === 0 ? 0 : value.sum / value.count]),
  );
}

export function computeCoverageMatrix(runs: AggregatedRun[], rubric: Rubric): Record<string, Record<string, {
  count: number;
  avgScore: number;
}>> {
  const weights = buildWeightMap(rubric);
  const totals = new Map<string, Map<string, { sum: number; count: number }>>();

  for (const run of runs) {
    for (const output of run.outputs) {
      const pointwise = output.judgments.filter((judgment) => judgment.mode === 'POINTWISE');
      if (pointwise.length === 0) {
        continue;
      }

      const composite = pointwise.reduce((acc, judgment) => {
        return (
          acc +
          Object.entries(judgment.scores).reduce((subtotal, [criterion, value]) => {
            const weight = weights[criterion] ?? 0;
            const numeric = toFiniteNumber(value);
            return subtotal + weight * numeric;
          }, 0)
        );
      }, 0) / pointwise.length;

      const tags = output.tags.length > 0 ? output.tags : ['untagged'];
      const difficultyBucket = String(output.difficulty ?? 'unknown');

      for (const tag of tags) {
        if (!totals.has(tag)) {
          totals.set(tag, new Map());
        }
        const byDifficulty = totals.get(tag)!;
        const cell = byDifficulty.get(difficultyBucket) ?? { sum: 0, count: 0 };
        cell.sum += composite;
        cell.count += 1;
        byDifficulty.set(difficultyBucket, cell);
      }
    }
  }

  return Object.fromEntries(
    Array.from(totals.entries()).map(([tag, difficultyMap]) => [
      tag,
      Object.fromEntries(
        Array.from(difficultyMap.entries()).map(([difficulty, { sum, count }]) => [
          difficulty,
          {
            count,
            avgScore: count === 0 ? 0 : sum / count,
          },
        ]),
      ),
    ]),
  );
}

export interface PairwiseJudgmentInput {
  runIds: [string, string];
  winnerRunId: string | null;
}

export function computePairwiseRanking(judgments: PairwiseJudgmentInput[]): Record<string, {
  winRate: number;
  wins: number;
  losses: number;
  comparisons: number;
}> {
  const table: Record<string, { wins: number; losses: number; comparisons: number }> = {};

  for (const { runIds, winnerRunId } of judgments) {
    const participants = Array.from(new Set(runIds));
    if (participants.length < 2) {
      continue;
    }

    for (const runId of participants) {
      table[runId] = table[runId] ?? { wins: 0, losses: 0, comparisons: 0 };
      table[runId].comparisons += 1;
    }

    if (winnerRunId) {
      if (participants.includes(winnerRunId)) {
        table[winnerRunId].wins += 1;
        for (const runId of participants) {
          if (runId !== winnerRunId) {
            table[runId].losses += 1;
          }
        }
      }
    }
  }

  return Object.fromEntries(
    Object.entries(table).map(([runId, stats]) => [
      runId,
      {
        ...stats,
        winRate: stats.comparisons === 0 ? 0 : stats.wins / stats.comparisons,
      },
    ]),
  );
}

function buildWeightMap(rubric: Rubric): Record<string, number> {
  return rubric.reduce<Record<string, number>>((acc: Record<string, number>, criterion: RubricCriterion) => {
    acc[criterion.name] = criterion.weight;
    return acc;
  }, {});
}

function toFiniteNumber(value: unknown): number {
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}
