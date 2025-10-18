import type { ModelParams } from '@edison/shared';
import { z } from 'zod';

export const LLMMessageSchema = z.object({
  role: z.enum(['system', 'user', 'assistant']),
  content: z.string(),
});

export type LLMMessage = z.infer<typeof LLMMessageSchema>;

export const LLMResponseSchema = z.object({
  text: z.string(),
  usage: z.object({
    promptTokens: z.number().int().nonnegative(),
    completionTokens: z.number().int().nonnegative(),
    totalTokens: z.number().int().nonnegative(),
  }),
  latencyMs: z.number().int().nonnegative(),
  cached: z.boolean(),
  model: z.string(),
});

export type LLMResponse = z.infer<typeof LLMResponseSchema>;

export interface LLMAdapter {
  readonly provider: string;
  readonly modelId: string;
  chat(
    messages: LLMMessage[],
    options?: { params?: Partial<ModelParams>; seed?: number },
  ): Promise<LLMResponse>;
  estimateCost(promptTokens: number, completionTokens: number): number;
  validateModel(params?: Partial<ModelParams>): Promise<void>;
}
