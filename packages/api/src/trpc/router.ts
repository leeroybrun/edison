import { fetchRequestHandler } from '@trpc/server/adapters/fetch';
import { Hono } from 'hono';

import { createContextFactory, router as createRouter } from './context';
import { aiAssistRouter } from './routers/ai-assist';
import { authRouter } from './routers/auth';
import { datasetRouter } from './routers/dataset';
import { experimentRouter } from './routers/experiment';
import { projectRouter } from './routers/project';
import { promptRouter } from './routers/prompt';
import { providerRouter } from './routers/provider';
import { reviewRouter } from './routers/review';
import { runRouter } from './routers/run';

export const appRouter = createRouter({
  auth: authRouter,
  experiment: experimentRouter,
  dataset: datasetRouter,
  prompt: promptRouter,
  project: projectRouter,
  provider: providerRouter,
  run: runRouter,
  review: reviewRouter,
  aiAssist: aiAssistRouter,
});

export type AppRouter = typeof appRouter;

export function createTRPCMiddleware(deps: Parameters<typeof createContextFactory>[0]) {
  const createContext = createContextFactory(deps);
  const trpcApp = new Hono();

  trpcApp.all('/*', (c) =>
    fetchRequestHandler({
      endpoint: '/trpc',
      req: c.req.raw,
      router: appRouter,
      createContext: () => createContext(c),
    }),
  );

  return trpcApp;
}
