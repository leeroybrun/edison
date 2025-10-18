import type { ModelParams } from '@edison/shared';
import { VertexAI } from '@google-cloud/vertexai';

import { ValidationError } from '../../lib/errors';
import { readCachedResponse, writeCachedResponse } from '../cache';
import type { LLMAdapter, LLMMessage, LLMResponse } from '../types';

interface VertexConfig {
  projectId: string;
  location: string;
}

const pricingTable: Record<string, { input: number; output: number }> = {
  'gemini-1.5-pro': { input: 0.00125, output: 0.00375 },
  'gemini-1.5-flash': { input: 0.00018, output: 0.00054 },
};

export class VertexAdapter implements LLMAdapter {
  private readonly model: ReturnType<VertexAI['getGenerativeModel']>;

  constructor(
    apiKeyJson: string,
    public readonly provider: string,
    public readonly modelId: string,
    config: VertexConfig,
  ) {
    if (!config.projectId || !config.location) {
      throw new Error('Vertex adapter requires projectId and location in credential config');
    }

    const credentials = JSON.parse(apiKeyJson) as {
      client_email: string;
      private_key: string;
    };

    const vertex = new VertexAI({
      project: config.projectId,
      location: config.location,
      googleAuthOptions: { credentials },
    });

    this.model = vertex.getGenerativeModel({ model: modelId });
  }

  async chat(
    messages: LLMMessage[],
    options?: { params?: Partial<ModelParams>; seed?: number },
  ): Promise<LLMResponse> {
    const cached = await readCachedResponse(this.provider, this.modelId, messages, options?.params, options?.seed);
    if (cached) {
      return cached;
    }

    const contents = messages
      .filter((message) => message.content.trim().length > 0)
      .map((message) => ({
        role: message.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: message.content }],
      }));

    const start = performance.now();
    const response = await this.model.generateContent({
      contents,
      generationConfig: {
        temperature: options?.params?.temperature,
        maxOutputTokens: options?.params?.maxTokens,
        topP: options?.params?.topP,
        topK: options?.params?.topK,
        candidateCount: 1,
        seed: options?.seed,
      },
    });

    const text = response.response?.candidates
      ?.flatMap((candidate) => candidate.content?.parts ?? [])
      ?.map((part) => part.text ?? '')
      .join('\n')
      ?? '';

    const usage = {
      promptTokens: response.response?.usageMetadata?.promptTokenCount ?? 0,
      completionTokens: response.response?.usageMetadata?.candidatesTokenCount ?? 0,
      totalTokens: response.response?.usageMetadata?.totalTokenCount ??
        ((response.response?.usageMetadata?.promptTokenCount ?? 0) +
          (response.response?.usageMetadata?.candidatesTokenCount ?? 0)),
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
    const pricing = pricingTable[this.modelId] ?? { input: 0.001, output: 0.003 };
    return ((promptTokens * pricing.input) + (completionTokens * pricing.output)) / 1000;
  }

  async validateModel(params?: Partial<ModelParams>): Promise<void> {
    if (!this.modelId || !this.modelId.trim()) {
      throw new ValidationError('Model identifier is required for Vertex credentials.');
    }

    if (params?.temperature !== undefined && (params.temperature < 0 || params.temperature > 1)) {
      throw new ValidationError('Vertex temperature must be between 0 and 1.');
    }
  }
}
