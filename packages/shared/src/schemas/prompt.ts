import { z } from 'zod';

export const FewShotExampleSchema = z.object({
  user: z.string().min(1),
  assistant: z.string().min(1),
});

export const PromptSchema = z.object({
  name: z.string().min(1),
  systemText: z.string().optional(),
  text: z.string().min(1),
  fewShots: z.array(FewShotExampleSchema).optional(),
  toolsSchema: z.unknown().optional(),
});

export type FewShotExample = z.infer<typeof FewShotExampleSchema>;
export type PromptConfig = z.infer<typeof PromptSchema>;
