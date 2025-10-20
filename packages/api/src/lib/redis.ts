import Redis from 'ioredis';

import { getConfig } from './config';
import { logger } from './logger';

const { REDIS_URL } = getConfig();

export const redis = new Redis(REDIS_URL, {
  maxRetriesPerRequest: null,
  enableAutoPipelining: true,
});

redis.on('error', (error) => {
  logger.error({ err: error }, 'redis error');
});
