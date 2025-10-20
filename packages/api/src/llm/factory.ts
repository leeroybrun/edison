import { Prisma } from '@prisma/client';
import type { LLMProvider, PrismaClient, ProviderCredential } from '@prisma/client';

import { getConfig } from '../lib/config';
import { decrypt } from '../lib/crypto';
import { logger } from '../lib/logger';

import { AnthropicAdapter } from './adapters/anthropic';
import { AzureOpenAIAdapter } from './adapters/azure';
import { BedrockAdapter } from './adapters/bedrock';
import { OllamaAdapter } from './adapters/ollama';
import { OpenAIAdapter } from './adapters/openai';
import { OpenAICompatibleAdapter } from './adapters/openai-compatible';
import { VertexAdapter } from './adapters/vertex';
import type { LLMAdapter } from './types';

type ProviderConfig = Prisma.JsonValue | null | undefined;

export class LLMAdapterFactory {
  private readonly cache = new Map<string, LLMAdapter>();
  private readonly config = getConfig();

  constructor(private readonly prisma: PrismaClient) {}

  async getAdapter(credential: ProviderCredential, modelId: string): Promise<LLMAdapter> {
    const cacheKey = `${credential.id}:${modelId}`;
    const existing = this.cache.get(cacheKey);
    if (existing) {
      return existing;
    }

    const decrypted = await decrypt(credential.encryptedApiKey);
    const adapter = this.instantiateAdapter(credential.provider, modelId, decrypted, credential.config);
    this.cache.set(cacheKey, adapter);
    logger.debug({ provider: credential.provider, modelId }, 'created LLM adapter');
    return adapter;
  }

  async getCredentialForProject(
    projectId: string,
    provider: ProviderCredential['provider'],
    label?: string,
  ): Promise<ProviderCredential> {
    const credential = await this.tryGetCredentialForProject(projectId, provider, label);
    if (!credential) {
      throw new Error(`No active credential for provider ${provider} in project ${projectId}`);
    }
    return credential;
  }

  async tryGetCredentialForProject(
    projectId: string,
    provider: ProviderCredential['provider'],
    label?: string,
  ): Promise<ProviderCredential | null> {
    return this.prisma.providerCredential.findFirst({
      where: (
        {
          projectId,
          provider,
          isActive: true,
          deletedAt: null,
          ...(label ? { label } : {}),
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ) as any,
    });
  }

  async tryGetAdapterForProject(
    projectId: string,
    provider: ProviderCredential['provider'],
    modelId: string,
  ): Promise<LLMAdapter | null> {
    const credential = await this.tryGetCredentialForProject(projectId, provider);
    if (!credential) {
      return null;
    }
    return this.getAdapter(credential, modelId);
  }

  async getGlobalAdapter(provider: LLMProvider, modelId: string): Promise<LLMAdapter> {
    const cachedKey = `global:${provider}:${modelId}`;
    const existing = this.cache.get(cachedKey);
    if (existing) {
      return existing;
    }

    const adapter = await this.instantiateGlobalAdapter(provider, modelId);
    this.cache.set(cachedKey, adapter);
    return adapter;
  }

  async tryGetGlobalAdapter(provider: LLMProvider, modelId: string): Promise<LLMAdapter | null> {
    try {
      return await this.getGlobalAdapter(provider, modelId);
    } catch (error) {
      return null;
    }
  }

  private instantiateAdapter(
    provider: LLMProvider,
    modelId: string,
    decrypted: string,
    config: ProviderConfig,
  ): LLMAdapter {
    const parsedConfig =
      config && typeof config === 'object' && !Array.isArray(config) ? (config as Record<string, unknown>) : {};
    switch (provider) {
      case 'OPENAI':
        return new OpenAIAdapter(decrypted, provider, modelId);
      case 'ANTHROPIC':
        return new AnthropicAdapter(decrypted, provider, modelId);
      case 'AZURE_OPENAI':
        return new AzureOpenAIAdapter(decrypted, provider, modelId, parsedConfig as { endpoint: string; apiVersion?: string });
      case 'GOOGLE_VERTEX':
        return new VertexAdapter(decrypted, provider, modelId, parsedConfig as { projectId: string; location: string });
      case 'AWS_BEDROCK':
        return new BedrockAdapter(decrypted, provider, modelId, parsedConfig as { region: string });
      case 'OLLAMA':
        return new OllamaAdapter(decrypted || null, provider, modelId, parsedConfig as { baseUrl?: string });
      case 'OPENAI_COMPATIBLE':
        return new OpenAICompatibleAdapter(decrypted, provider, modelId, parsedConfig as { baseUrl: string; headers?: Record<string, string> });
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
  }

  private async instantiateGlobalAdapter(provider: LLMProvider, modelId: string): Promise<LLMAdapter> {
    switch (provider) {
      case 'OPENAI': {
        const key = this.config.OPENAI_API_KEY;
        if (!key) {
          throw new Error('OPENAI_API_KEY is not configured');
        }
        return new OpenAIAdapter(key, provider, modelId);
      }
      case 'ANTHROPIC': {
        const key = this.config.ANTHROPIC_API_KEY;
        if (!key) {
          throw new Error('ANTHROPIC_API_KEY is not configured');
        }
        return new AnthropicAdapter(key, provider, modelId);
      }
      default:
        throw new Error(`Global adapter not supported for provider ${provider}`);
    }
  }
}
