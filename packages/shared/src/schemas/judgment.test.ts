import { describe, expect, it } from 'vitest';
import { JudgmentResultSchema } from './judgment';

describe('JudgmentResultSchema', () => {
  it('provides default safety flags when omitted', () => {
    const parsed = JudgmentResultSchema.parse({
      scores: { accuracy: 4.5 },
      rationales: { accuracy: 'Correctness verified against ground truth.' },
      safetyFlags: {},
    });

    expect(parsed.safetyFlags).toMatchObject({
      policyViolation: false,
      piiDetected: false,
      toxicContent: false,
      jailbreakAttempt: false,
    });
  });

  it('rejects scores outside of allowed bounds', () => {
    const result = JudgmentResultSchema.safeParse({
      scores: { accuracy: 8 },
      rationales: { accuracy: 'Way too confident.' },
      safetyFlags: {},
    });

    expect(result.success).toBe(false);
    expect(result.success ? [] : result.error.issues[0]?.path).toEqual([
      'scores',
      'accuracy',
    ]);
  });
});
