import type { ModelParams } from '@edison/shared';

import { readCachedResponse, writeCachedResponse } from '../cache';
import type { LLMAdapter, LLMMessage, LLMResponse } from '../types';

interface AzureConfig {
  endpoint: string;
  apiVersion?: string;
}

const pricingTable: Record<string, { input: number; output: number }> = {
  'gpt-4o': { input: 0.0025, output: 0.01 },
  'gpt-35-turbo': { input: 0.0015, output: 0.002 },
};

export class AzureOpenAIAdapter implements LLMAdapter {
  private readonly endpoint: string;
  private readonly apiVersion: string;

  constructor(
    private readonly apiKey: string,
    public readonly provider: string,
    public readonly modelId: string,
    config: AzureConfig,
  ) {
    if (!config.endpoint) {
      throw new Error('Azure OpenAI endpoint is required in provider credential config');
    }
    this.endpoint = config.endpoint.replace(/\/$/, '');
    this.apiVersion = config.apiVersion ?? '2024-02-15-preview';
  }

  async chat(
    messages: LLMMessage[],
    options?: { params?: Partial<ModelParams>; seed?: number },
  ): Promise<LLMResponse> {
    const cached = await readCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed);
    if (cached) {
      return cached;
    }

    const url = `${this.endpoint}/openai/deployments/${this.modelId}/chat/completions?api-version=${this.apiVersion}`;
    const body: Record<string, unknown> = {
      messages,
      temperature: options?.params?.temperature,
      max_tokens: options?.params?.maxTokens,
      top_p: options?.params?.topP,
      frequency_penalty: options?.params?.frequencyPenalty,
      presence_penalty: options?.params?.presencePenalty,
    };

    if (options?.seed !== undefined) {
      body.seed = options.seed;
    }

    const start = performance.now();
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'api-key': this.apiKey,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Azure OpenAI error: ${response.status} ${errorText}`);
    }

    const data = (await response.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
      usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
    };

    const text = data.choices?.[0]?.message?.content ?? '';
    const usage = {
      promptTokens: data.usage?.prompt_tokens ?? 0,
      completionTokens: data.usage?.completion_tokens ?? 0,
      totalTokens: data.usage?.total_tokens ?? 0,
    };

    const result: LLMResponse = {
      text,
      usage,
      latencyMs: Math.round(performance.now() - start),
      cached: false,
      model: this.modelId,
    };

    await writeCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed, result);
    return result;
  }

  estimateCost(promptTokens: number, completionTokens: number): number {
    const pricing = pricingTable[this.modelId] ?? { input: 0.0015, output: 0.0025 };
    return ((promptTokens * pricing.input) + (completionTokens * pricing.output)) / 1000;
  }
}
