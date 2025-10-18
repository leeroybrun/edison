import type { PrismaClient } from '@prisma/client';
import type { Context } from 'hono';

import { appEvents, type IterationEvent } from '../lib/events';
import { logger } from '../lib/logger';

const encoder = new TextEncoder();

export function serializeSSEEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

type IterationSnapshot = {
  iterationId: string;
  status: string;
  startedAt: string | null;
  finishedAt: string | null;
  metrics: Record<string, unknown> | null;
  totalRuns: number;
  completedRuns: number;
  failedRuns: number;
};

async function getIterationSnapshot(prisma: PrismaClient, iterationId: string): Promise<IterationSnapshot | null> {
  const iteration = await prisma.iteration.findUnique({
    where: { id: iterationId },
    include: { modelRuns: true },
  });

  if (!iteration) {
    return null;
  }

  const completedRuns = iteration.modelRuns.filter((run) => run.status === 'COMPLETED').length;
  const failedRuns = iteration.modelRuns.filter((run) => run.status === 'FAILED').length;

  return {
    iterationId,
    status: iteration.status,
    startedAt: iteration.startedAt?.toISOString() ?? null,
    finishedAt: iteration.finishedAt?.toISOString() ?? null,
    metrics: iteration.metrics as Record<string, unknown> | null,
    totalRuns: iteration.modelRuns.length,
    completedRuns,
    failedRuns,
  };
}

function bindIterationEvents(iterationId: string, send: (event: string, data: unknown) => void) {
  const listener = (payload: IterationEvent) => {
    if (payload.iterationId !== iterationId) {
      return;
    }
    send(payload.type, payload.payload);
  };

  appEvents.on('iteration:event', listener);

  return () => {
    appEvents.off('iteration:event', listener);
  };
}

export function createIterationStreamHandler(prisma: PrismaClient) {
  return async (c: Context) => {
    const iterationId = c.req.param('id');
    if (!iterationId) {
      return c.json({ error: 'Missing iteration id' }, 400);
    }

    const snapshot = await getIterationSnapshot(prisma, iterationId);
    if (!snapshot) {
      return c.json({ error: 'Iteration not found' }, 404);
    }

    let cleanup = () => {};

    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const send = (event: string, data: unknown) => {
          controller.enqueue(encoder.encode(serializeSSEEvent(event, data)));
        };

        controller.enqueue(encoder.encode(': connected\n\n'));
        send('snapshot', snapshot);

        const unbind = bindIterationEvents(iterationId, send);
        const heartbeat = setInterval(() => {
          send('heartbeat', { timestamp: Date.now() });
        }, 15000);

        cleanup = () => {
          clearInterval(heartbeat);
          unbind();
        };
      },
      cancel(reason) {
        if (reason) {
          logger.debug({ iterationId, reason }, 'iteration SSE stream cancelled');
        }
        cleanup();
      },
    });

    const headers = new Headers({
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
    });

    return c.newResponse(stream, { status: 200, headers });
  };
}
