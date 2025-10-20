import { describe, expect, it } from 'vitest';
import { DatasetSchema } from './dataset';

describe('DatasetSchema', () => {
  it('applies defaults to dataset cases', () => {
    const parsed = DatasetSchema.parse({
      projectId: 'proj_123',
      name: 'Golden set',
      kind: 'GOLDEN',
      cases: [
        {
          input: { question: 'What is the capital of France?' },
        },
      ],
    });

    expect(parsed.cases[0]).toMatchObject({
      tags: [],
      difficulty: 3,
      metadata: {},
    });
  });

  it('fails when cases have missing input payloads', () => {
    const result = DatasetSchema.safeParse({
      projectId: 'proj_123',
      name: 'Invalid dataset',
      kind: 'SYNTHETIC',
      cases: [
        {
          // @ts-expect-error - validating runtime behaviour
          input: undefined,
        },
      ],
    });

    expect(result.success).toBe(false);
    expect(result.success ? [] : result.error.issues[0]?.path).toEqual([
      'cases',
      0,
      'input',
    ]);
  });
});
