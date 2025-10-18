import type { ModelParams } from '@edison/shared';

import { readCachedResponse, writeCachedResponse } from '../cache';
import type { LLMAdapter, LLMMessage, LLMResponse } from '../types';

interface CompatibleConfig {
  baseUrl: string;
  headers?: Record<string, string>;
}

export class OpenAICompatibleAdapter implements LLMAdapter {
  private readonly baseUrl: string;
  private readonly extraHeaders: Record<string, string>;

  constructor(
    private readonly apiKey: string,
    public readonly provider: string,
    public readonly modelId: string,
    config: CompatibleConfig,
  ) {
    if (!config.baseUrl) {
      throw new Error('OpenAI-compatible adapter requires baseUrl in credential config');
    }
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.extraHeaders = config.headers ?? {};
  }

  async chat(
    messages: LLMMessage[],
    options?: { params?: Partial<ModelParams>; seed?: number },
  ): Promise<LLMResponse> {
    const cached = await readCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed);
    if (cached) {
      return cached;
    }

    const url = `${this.baseUrl}/v1/chat/completions`;
    const body: Record<string, unknown> = {
      model: this.modelId,
      messages,
      temperature: options?.params?.temperature,
      max_tokens: options?.params?.maxTokens,
      top_p: options?.params?.topP,
      stop: options?.params?.stop,
    };

    if (options?.seed !== undefined) {
      body.seed = options.seed;
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${this.apiKey}`,
      ...this.extraHeaders,
    };

    const start = performance.now();
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenAI-compatible error: ${response.status} ${errorText}`);
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
    const defaultPricing = { input: 0.001, output: 0.002 };
    return ((promptTokens * defaultPricing.input) + (completionTokens * defaultPricing.output)) / 1000;
  }
}
