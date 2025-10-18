import type Redis from 'ioredis';

import { RateLimitError } from '../lib/errors';

export interface RateLimitOptions {
  key: string;
  limit: number;
  windowMs: number;
}

export class RateLimiter {
  constructor(private readonly redis: Redis) {}

  async consume(options: RateLimitOptions): Promise<{ remaining: number; resetAt: number }> {
    const redisKey = `ratelimit:${options.key}`;
    const ttlMs = options.windowMs;
    const current = await this.redis.incr(redisKey);

    if (current === 1) {
      await this.redis.pexpire(redisKey, ttlMs);
    }

    if (current > options.limit) {
      const ttl = await this.redis.pttl(redisKey);
      const resetAt = Date.now() + (ttl > 0 ? ttl : ttlMs);
      throw new RateLimitError('Too many attempts. Please try again later.', {
        remaining: 0,
        resetAt,
      });
    }

    const ttl = await this.redis.pttl(redisKey);
    const resetAt = Date.now() + (ttl > 0 ? ttl : ttlMs);
    return { remaining: Math.max(options.limit - current, 0), resetAt };
  }
}
