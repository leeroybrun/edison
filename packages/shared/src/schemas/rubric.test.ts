import { describe, expect, it } from 'vitest';
import { RubricSchema } from './rubric';

describe('RubricSchema', () => {
  it('accepts criteria whose weights sum to 1 within tolerance', () => {
    const rubric = RubricSchema.parse([
      {
        name: 'Accuracy',
        description: 'How factually correct the answer is',
        weight: 0.6,
        scale: {
          min: 1,
          max: 5,
          labels: {
            '1': 'Poor',
            '3': 'Acceptable',
            '5': 'Excellent',
          },
        },
      },
      {
        name: 'Tone',
        description: 'How well the assistant matches the requested tone',
        weight: 0.4,
        scale: {
          min: 1,
          max: 5,
        },
      },
    ]);

    expect(rubric).toHaveLength(2);
  });

  it('rejects criteria when weights are not normalized', () => {
    expect(() =>
      RubricSchema.parse([
        {
          name: 'Accuracy',
          description: 'How factually correct the answer is',
          weight: 0.5,
          scale: {
            min: 0,
            max: 10,
          },
        },
        {
          name: 'Tone',
          description: 'How well the assistant matches the requested tone',
          weight: 0.6,
          scale: {
            min: 0,
            max: 10,
          },
        },
      ]),
    ).toThrowError(/weights must sum to 1\.0/);
  });
});
