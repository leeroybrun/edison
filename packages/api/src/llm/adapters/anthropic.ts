import type { ModelParams } from '@edison/shared';

import { readCachedResponse, writeCachedResponse } from '../cache';
import type { LLMAdapter, LLMMessage, LLMResponse } from '../types';

type AnthropicMessage = {
  role: 'user' | 'assistant';
  content: Array<{ type: 'text'; text: string }>;
};

const pricingTable: Record<string, { input: number; output: number }> = {
  'claude-3-5-sonnet-20240620': { input: 0.003, output: 0.015 },
  'claude-3-haiku-20240307': { input: 0.00025, output: 0.00125 },
};

function toAnthropicMessages(messages: LLMMessage[]): { system?: string; messages: AnthropicMessage[] } {
  const result: AnthropicMessage[] = [];
  let system: string | undefined;

  for (const message of messages) {
    if (message.role === 'system') {
      system = system ? `${system}\n${message.content}` : message.content;
      continue;
    }

    result.push({
      role: message.role === 'assistant' ? 'assistant' : 'user',
      content: [{ type: 'text', text: message.content }],
    });
  }

  return { system, messages: result };
}

export class AnthropicAdapter implements LLMAdapter {
  constructor(
    private readonly apiKey: string,
    public readonly provider: string,
    public readonly modelId: string,
  ) {}

  async chat(
    messages: LLMMessage[],
    options?: { params?: Partial<ModelParams>; seed?: number },
  ): Promise<LLMResponse> {
    const cached = await readCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed);
    if (cached) {
      return cached;
    }

    const payload = toAnthropicMessages(messages);
    const body: Record<string, unknown> = {
      model: this.modelId,
      messages: payload.messages,
      max_tokens: options?.params?.maxTokens ?? 1024,
      temperature: options?.params?.temperature ?? 0.7,
      top_p: options?.params?.topP,
      top_k: options?.params?.topK,
    };

    if (payload.system) {
      body.system = payload.system;
    }

    if (options?.seed !== undefined) {
      body.metadata = { seed: options.seed };
    }

    const start = performance.now();
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Anthropic API error: ${response.status} ${errorText}`);
    }

    const data = (await response.json()) as {
      id: string;
      content?: Array<{ text?: string }>;
      usage?: { input_tokens?: number; output_tokens?: number };
      model?: string;
    };

    const text = (data.content ?? []).map((part) => part.text ?? '').join('\n');
    const usage = {
      promptTokens: data.usage?.input_tokens ?? 0,
      completionTokens: data.usage?.output_tokens ?? 0,
      totalTokens: (data.usage?.input_tokens ?? 0) + (data.usage?.output_tokens ?? 0),
    };

    const result: LLMResponse = {
      text,
      usage,
      latencyMs: Math.round(performance.now() - start),
      cached: false,
      model: data.model ?? this.modelId,
    };

    await writeCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed, result);
    return result;
  }

  estimateCost(promptTokens: number, completionTokens: number): number {
    const pricing = pricingTable[this.modelId] ?? { input: 0.0015, output: 0.006 }; // USD per 1K tokens
    return ((promptTokens * pricing.input) + (completionTokens * pricing.output)) / 1000;
  }
}
