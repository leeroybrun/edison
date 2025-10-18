import { z } from 'zod';

export const SafetyFlagsSchema = z.object({
  policyViolation: z.boolean().default(false),
  piiDetected: z.boolean().default(false),
  toxicContent: z.boolean().default(false),
  jailbreakAttempt: z.boolean().default(false),
});

export const PointwiseScoresSchema = z.record(z.string(), z.number().min(0).max(5));
export const RationalesSchema = z.record(z.string(), z.string().max(500));

export const JudgmentResultSchema = z.object({
  scores: PointwiseScoresSchema,
  rationales: RationalesSchema,
  safetyFlags: SafetyFlagsSchema,
});

export type SafetyFlags = z.infer<typeof SafetyFlagsSchema>;
export type PointwiseScores = z.infer<typeof PointwiseScoresSchema>;
export type Rationales = z.infer<typeof RationalesSchema>;
export type JudgmentResult = z.infer<typeof JudgmentResultSchema>;
