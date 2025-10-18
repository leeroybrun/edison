import { z } from 'zod';

export const RubricScaleSchema = z.object({
  min: z.number(),
  max: z.number(),
  labels: z
    .record(z.string())
    .optional()
    .describe('Mapping of numeric score to human-readable label'),
});

export const RubricCriterionSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().min(1).max(500),
  weight: z.number().min(0).max(1),
  scale: RubricScaleSchema,
});

export const RubricSchema = z
  .array(RubricCriterionSchema)
  .min(1)
  .refine((criteria) => {
    const totalWeight = criteria.reduce((sum, criterion) => sum + criterion.weight, 0);
    return Math.abs(totalWeight - 1) < 0.01;
  }, 'Rubric weights must sum to 1.0 ±0.01.');

export type RubricScale = z.infer<typeof RubricScaleSchema>;
export type RubricCriterion = z.infer<typeof RubricCriterionSchema>;
export type Rubric = z.infer<typeof RubricSchema>;
