import { describe, expect, it } from 'vitest';
import type { Rubric } from '@edison/shared';
import {
  analyzeFacets,
  bootstrapConfidenceIntervals,
  calculateCompositeScores,
  computeCoverageMatrix,
  computePairwiseRanking,
  type AggregatedRun,
} from '../src/services/aggregator-math';

describe('aggregator math helpers', () => {
  const rubric: Rubric = [
    {
      name: 'Helpfulness',
      description: 'Is the answer helpful?',
      weight: 0.6,
      scale: { min: 0, max: 5 },
    },
    {
      name: 'Accuracy',
      description: 'Is the answer accurate?',
      weight: 0.4,
      scale: { min: 0, max: 5 },
    },
  ];

  const runs: AggregatedRun[] = [
    {
      id: 'runA',
      outputs: [
        {
          tags: ['billing', 'priority-high'],
          difficulty: 4,
          judgments: [
            { mode: 'POINTWISE', scores: { Helpfulness: 4, Accuracy: 5 } },
            { mode: 'POINTWISE', scores: { Helpfulness: 3, Accuracy: 4 } },
          ],
        },
      ],
    },
    {
      id: 'runB',
      outputs: [
        {
          tags: ['billing'],
          difficulty: 2,
          judgments: [
            { mode: 'POINTWISE', scores: { Helpfulness: 2, Accuracy: 3 } },
            { mode: 'POINTWISE', scores: { Helpfulness: 3, Accuracy: 3 } },
          ],
        },
      ],
    },
  ];

  it('computes weighted composite scores', () => {
    const scores = calculateCompositeScores(runs, rubric);
    expect(scores.runA).toBeCloseTo((4 * 0.6 + 5 * 0.4 + 3 * 0.6 + 4 * 0.4) / 2, 5);
    expect(scores.runB).toBeCloseTo((2 * 0.6 + 3 * 0.4 + 3 * 0.6 + 3 * 0.4) / 2, 5);
  });

  it('produces deterministic bootstrap intervals for the same seed', () => {
    const first = bootstrapConfidenceIntervals(runs, rubric, { seed: 'iteration-1', samples: 200 });
    const second = bootstrapConfidenceIntervals(runs, rubric, { seed: 'iteration-1', samples: 200 });
    expect(first).toStrictEqual(second);
    expect(first.runA.lower).toBeLessThanOrEqual(first.runA.upper);
  });

  it('aggregates facet averages by tag', () => {
    const facets = analyzeFacets(runs, rubric);
    expect(facets['priority-high']).toBeCloseTo(3.9, 5);
    expect(facets['billing']).toBeCloseTo((3.9 + 2.7) / 2, 5);
  });

  it('builds a coverage matrix by tag and difficulty bucket', () => {
    const matrix = computeCoverageMatrix(runs, rubric);
    expect(matrix['priority-high']?.['4']?.count).toBe(1);
    expect(matrix['priority-high']?.['4']?.avgScore).toBeCloseTo(3.9, 5);
    expect(matrix['billing']?.['2']?.count).toBe(1);
    expect(matrix['billing']?.['2']?.avgScore).toBeCloseTo(2.7, 5);
  });

  it('computes pairwise ranking with win/loss breakdown', () => {
    const ranking = computePairwiseRanking([
      { runIds: ['runA', 'runB'], winnerRunId: 'runA' },
      { runIds: ['runA', 'runB'], winnerRunId: 'runB' },
      { runIds: ['runA', 'runB'], winnerRunId: 'runA' },
    ]);

    expect(ranking.runA.wins).toBe(2);
    expect(ranking.runA.losses).toBe(1);
    expect(ranking.runA.winRate).toBeCloseTo(2 / 3, 5);
    expect(ranking.runB.wins).toBe(1);
    expect(ranking.runB.losses).toBe(2);
  });
});
