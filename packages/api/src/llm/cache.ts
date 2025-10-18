import { createHash } from 'crypto';

import type { ModelParams } from '@edison/shared';

import { redis } from '../lib/redis';

import type { LLMMessage, LLMResponse } from './types';

function buildCacheKey(
  provider: string,
  modelId: string,
  messages: LLMMessage[],
  params?: Partial<ModelParams>,
  seed?: number,
): string {
  const payload = JSON.stringify({ provider, modelId, messages, params, seed });
  return createHash('sha256').update(payload).digest('hex');
}

export async function readCachedResponse(
  provider: string,
  modelId: string,
  messages: LLMMessage[],
  params?: Partial<ModelParams>,
  seed?: number,
): Promise<(LLMResponse & { cached: true }) | null> {
  const key = buildCacheKey(provider, modelId, messages, params, seed);
  const cached = await redis.get(key);
  if (!cached) {
    return null;
  }

  const parsed = JSON.parse(cached) as LLMResponse;
  return { ...parsed, cached: true };
}

export async function writeCachedResponse(
  provider: string,
  modelId: string,
  messages: LLMMessage[],
  params: Partial<ModelParams> | undefined,
  seed: number | undefined,
  response: LLMResponse,
  ttlSeconds = 3600,
): Promise<void> {
  const key = buildCacheKey(provider, modelId, messages, params, seed);
  await redis.set(key, JSON.stringify({ ...response, cached: false }), 'EX', ttlSeconds);
}
