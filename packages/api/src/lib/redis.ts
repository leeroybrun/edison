import Redis from 'ioredis';

import { getConfig } from './config';
import { logger } from './logger';

const { REDIS_URL } = getConfig();

export const redis = new Redis(REDIS_URL, {
  maxRetriesPerRequest: 2,
  enableAutoPipelining: true,
});

redis.on('error', (error) => {
  logger.error({ err: error }, 'redis error');
});
