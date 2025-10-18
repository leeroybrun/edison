import {
  BedrockRuntimeClient,
  ConverseCommand,
  type Message as BedrockMessage,
} from '@aws-sdk/client-bedrock-runtime';
import type { ModelParams } from '@edison/shared';

import { readCachedResponse, writeCachedResponse } from '../cache';
import type { LLMAdapter, LLMMessage, LLMResponse } from '../types';

interface BedrockCredentials {
  accessKeyId: string;
  secretAccessKey: string;
  sessionToken?: string;
}

interface BedrockConfig {
  region: string;
}

const pricingTable: Record<string, { input: number; output: number }> = {
  'anthropic.claude-3-sonnet-20240229-v1:0': { input: 0.003, output: 0.015 },
};

export class BedrockAdapter implements LLMAdapter {
  private readonly client: BedrockRuntimeClient;

  constructor(
    credentialsJson: string,
    public readonly provider: string,
    public readonly modelId: string,
    config: BedrockConfig,
  ) {
    if (!config.region) {
      throw new Error('Bedrock adapter requires region in credential config');
    }

    const credentials = JSON.parse(credentialsJson) as BedrockCredentials;
    this.client = new BedrockRuntimeClient({
      region: config.region,
      credentials,
    });
  }

  async chat(
    messages: LLMMessage[],
    options?: { params?: Partial<ModelParams>; seed?: number },
  ): Promise<LLMResponse> {
    const cached = await readCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed);
    if (cached) {
      return cached;
    }

    const bedrockMessages: BedrockMessage[] = messages
      .filter((message) => message.content.trim().length > 0)
      .map((message) => ({
        role: message.role === 'assistant' ? 'assistant' : 'user',
        content: [{ text: message.content }],
      }));

    const command = new ConverseCommand({
      modelId: this.modelId,
      messages: bedrockMessages,
      inferenceConfig: {
        maxTokens: options?.params?.maxTokens,
        temperature: options?.params?.temperature,
        topP: options?.params?.topP,
        topK: options?.params?.topK,
      },
    });

    const start = performance.now();
    const response = await this.client.send(command);

    const text = response.output?.message?.content
      ?.map((part) => part.text ?? '')
      .join('\n')
      ?? '';

    const usage = {
      promptTokens: response.usage?.inputTokens ?? 0,
      completionTokens: response.usage?.outputTokens ?? 0,
      totalTokens: (response.usage?.inputTokens ?? 0) + (response.usage?.outputTokens ?? 0),
    };

    const result: LLMResponse = {
      text,
      usage,
      latencyMs: Math.round(performance.now() - start),
      cached: false,
      model: response.output?.modelId ?? this.modelId,
    };

    await writeCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed, result);
    return result;
  }

  estimateCost(promptTokens: number, completionTokens: number): number {
    const pricing = pricingTable[this.modelId] ?? { input: 0.003, output: 0.015 };
    return ((promptTokens * pricing.input) + (completionTokens * pricing.output)) / 1000;
  }
}
