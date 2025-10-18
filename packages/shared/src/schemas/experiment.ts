import { z } from 'zod';
import { RubricSchema } from './rubric';

export const StopRulesSchema = z.object({
  maxIterations: z.number().int().min(1).max(100).default(10),
  minDeltaThreshold: z.number().min(0).max(1).default(0.02),
  maxBudgetUsd: z.number().min(0).optional(),
  maxTotalTokens: z.number().int().min(0).optional(),
  convergenceWindow: z.number().int().min(2).default(3),
});

export const ModelParamsSchema = z.object({
  temperature: z.number().min(0).max(2).default(1),
  maxTokens: z.number().int().min(1).max(100000).optional(),
  topP: z.number().min(0).max(1).optional(),
  topK: z.number().int().min(0).optional(),
  frequencyPenalty: z.number().min(-2).max(2).optional(),
  presencePenalty: z.number().min(-2).max(2).optional(),
  stop: z.array(z.string().min(1)).min(1).max(4).optional(),
});

export const RubricConfigSchema = z.object({
  goal: z.string().min(10),
  rubric: RubricSchema,
  stopRules: StopRulesSchema,
});

export type StopRules = z.infer<typeof StopRulesSchema>;
export type ModelParams = z.infer<typeof ModelParamsSchema>;
export type RubricConfig = z.infer<typeof RubricConfigSchema>;
