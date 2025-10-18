import { z } from 'zod';

export const DatasetKindSchema = z.enum(['GOLDEN', 'SYNTHETIC', 'ADVERSARIAL']);

export const DatasetCaseSchema = z.object({
  input: z.record(z.string(), z.unknown()),
  expected: z.record(z.string(), z.unknown()).optional(),
  tags: z.array(z.string().min(1)).default([]),
  difficulty: z.number().int().min(1).max(5).default(3),
  metadata: z.record(z.string(), z.unknown()).default({}),
});

export const DatasetSchema = z.object({
  projectId: z.string().min(1),
  name: z.string().min(1),
  kind: DatasetKindSchema,
  description: z.string().optional(),
  metadata: z.record(z.string(), z.unknown()).default({}),
  cases: z.array(DatasetCaseSchema).default([]),
});

export type DatasetKind = z.infer<typeof DatasetKindSchema>;
export type DatasetCase = z.infer<typeof DatasetCaseSchema>;
export type Dataset = z.infer<typeof DatasetSchema>;
