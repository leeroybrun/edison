import { describe, expect, it } from 'vitest';
import { RubricSchema } from './rubric';
import { RubricConfigSchema } from './experiment';

describe('RubricConfigSchema', () => {
  const rubric = RubricSchema.parse([
    {
      name: 'Accuracy',
      description: 'Measures factual alignment with reference answers.',
      weight: 0.7,
      scale: { min: 1, max: 5 },
    },
    {
      name: 'Tone',
      description: 'Measures tone alignment with brand guidelines.',
      weight: 0.3,
      scale: { min: 1, max: 5 },
    },
  ]);

  it('fills defaults for stop rules when omitted', () => {
    const parsed = RubricConfigSchema.parse({
      goal: 'Deliver accurate and friendly answers to user questions.',
      rubric,
      stopRules: {},
    });

    expect(parsed.stopRules).toMatchObject({
      maxIterations: 10,
      minDeltaThreshold: 0.02,
      convergenceWindow: 3,
    });
  });

  it('rejects invalid stop rule configuration', () => {
    const result = RubricConfigSchema.safeParse({
      goal: 'Deliver accurate and friendly answers to user questions.',
      rubric,
      stopRules: {
        maxIterations: 0,
      },
    });

    expect(result.success).toBe(false);
    expect(result.success ? [] : result.error.issues[0]?.path).toEqual([
      'stopRules',
      'maxIterations',
    ]);
  });
});
