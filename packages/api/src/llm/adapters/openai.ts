import OpenAI from 'openai';

import { readCachedResponse, writeCachedResponse } from '../cache';
import type { LLMAdapter, LLMMessage, LLMResponse } from '../types';


const pricingTable: Record<string, { input: number; output: number }> = {
  'gpt-4o': { input: 0.0025, output: 0.01 },
  'gpt-4o-mini': { input: 0.00015, output: 0.0006 },
};

export class OpenAIAdapter implements LLMAdapter {
  private readonly client: OpenAI;

  constructor(
    private readonly apiKey: string,
    public readonly provider: string,
    public readonly modelId: string
  ) {
    this.client = new OpenAI({ apiKey });
  }

  async chat(
    messages: LLMMessage[],
    options?: { params?: Partial<ModelParams>; seed?: number },
  ): Promise<LLMResponse> {
    const cached = await readCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed);
    if (cached) {
      return cached;
    }

    const start = performance.now();
    const response = await this.client.chat.completions.create({
      model: this.modelId,
      messages,
      temperature: options?.params?.temperature,
      max_tokens: options?.params?.maxTokens,
      top_p: options?.params?.topP,
      seed: options?.seed,
    });

    const text = response.choices[0]?.message?.content ?? '';
    const usage = {
      promptTokens: response.usage?.prompt_tokens ?? 0,
      completionTokens: response.usage?.completion_tokens ?? 0,
      totalTokens: response.usage?.total_tokens ?? 0,
    };

    const payload: LLMResponse = {
      text,
      usage,
      latencyMs: Math.round(performance.now() - start),
      cached: false,
      model: response.model,
    };

    await writeCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed, payload);
    return payload;
  }

  estimateCost(promptTokens: number, completionTokens: number): number {
    const pricing = pricingTable[this.modelId] ?? { input: 0.001, output: 0.002 };
    return ((promptTokens * pricing.input) + (completionTokens * pricing.output)) / 1000;
  }
}
