import type { ModelParams } from '@edison/shared';

import { ValidationError } from '../../lib/errors';
import { readCachedResponse, writeCachedResponse } from '../cache';
import type { LLMAdapter, LLMMessage, LLMResponse } from '../types';

interface OllamaConfig {
  baseUrl?: string;
}

export class OllamaAdapter implements LLMAdapter {
  private readonly baseUrl: string;

  constructor(
    private readonly apiKey: string | null,
    public readonly provider: string,
    public readonly modelId: string,
    config: OllamaConfig = {},
  ) {
    this.baseUrl = (config.baseUrl ?? 'http://127.0.0.1:11434').replace(/\/$/, '');
  }

  async chat(
    messages: LLMMessage[],
    options?: { params?: Partial<ModelParams>; seed?: number },
  ): Promise<LLMResponse> {
    const cached = await readCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed);
    if (cached) {
      return cached;
    }

    const body = {
      model: this.modelId,
      messages,
      stream: false,
      options: {
        temperature: options?.params?.temperature,
        num_predict: options?.params?.maxTokens,
      },
    };

    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (this.apiKey) {
      headers.Authorization = `Bearer ${this.apiKey}`;
    }

    const start = performance.now();
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Ollama error: ${response.status} ${errorText}`);
    }

    const data = (await response.json()) as {
      message?: { content?: string };
      response?: string;
      prompt_eval_count?: number;
      eval_count?: number;
    };

    const text = data.message?.content ?? data.response ?? '';
    const usage = {
      promptTokens: data.prompt_eval_count ?? 0,
      completionTokens: data.eval_count ?? 0,
      totalTokens: (data.prompt_eval_count ?? 0) + (data.eval_count ?? 0),
    };

    const result: LLMResponse = {
      text,
      usage,
      latencyMs: Math.round(performance.now() - start),
      cached: false,
      model: this.modelId,
    };

    await writeCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed, result, 300);
    return result;
  }

  estimateCost(): number {
    return 0; // Local models have no incremental token cost
  }

  async validateModel(params?: Partial<ModelParams>): Promise<void> {
    if (!this.modelId || !this.modelId.trim()) {
      throw new ValidationError('Model identifier is required for Ollama credentials.');
    }

    if (params?.temperature !== undefined && (params.temperature < 0 || params.temperature > 2)) {
      throw new ValidationError('Ollama temperature must be between 0 and 2.');
    }
  }
}
