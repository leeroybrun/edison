import { randomUUID } from 'crypto';

import type Redis from 'ioredis';

import { logger } from './logger';

const RELEASE_SCRIPT = `
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
else
  return 0
end
`;

export class LockManager {
  constructor(private readonly redis: Redis) {}

  async withLock<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
    const token = randomUUID();
    const lockKey = `lock:${key}`;
    const acquisitionDeadline = Date.now() + ttlMs;

    const acquired = await this.tryAcquire(lockKey, token, ttlMs, acquisitionDeadline);
    if (!acquired) {
      throw new Error(`Failed to acquire lock for ${key}`);
    }

    try {
      return await fn();
    } finally {
      await this.release(lockKey, token);
    }
  }

  private async tryAcquire(
    lockKey: string,
    token: string,
    ttlMs: number,
    deadline: number,
  ): Promise<boolean> {
    while (Date.now() < deadline) {
      const acquired = await this.redis.set(lockKey, token, 'PX', ttlMs, 'NX');
      if (acquired) {
        return true;
      }
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    return false;
  }

  private async release(lockKey: string, token: string): Promise<void> {
    try {
      await this.redis.eval(RELEASE_SCRIPT, 1, lockKey, token);
    } catch (error) {
      logger.error({ lockKey, err: error }, 'failed to release lock');
    }
  }
}
