import { Queue } from 'bullmq';
import type { Redis } from 'ioredis';

import { logger } from '../lib/logger';

export type EdisonQueues = {
  execute: Queue;
  judge: Queue;
  aggregate: Queue;
  refine: Queue;
  generate: Queue;
  safety: Queue;
};

export function createQueues(connection: Redis): EdisonQueues {
  const queues: EdisonQueues = {
    execute: new Queue('execute-run', { connection }),
    judge: new Queue('judge-outputs', { connection }),
    aggregate: new Queue('aggregate-iteration', { connection }),
    refine: new Queue('refine-prompt', { connection }),
    generate: new Queue('generate-dataset', { connection }),
    safety: new Queue('safety-scan', { connection }),
  };

  for (const queue of Object.values(queues)) {
    queue.on('error', (error) => {
      logger.error({ err: error, queue: queue.name }, 'queue error');
    });
  }

  return queues;
}
