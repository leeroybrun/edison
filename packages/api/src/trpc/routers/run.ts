import { z } from 'zod';

import { protectedProcedure, router } from '../context';
import { assertExperimentMembership } from '../utils/authorization';

export const runRouter = router({
  listByExperiment: protectedProcedure
    .input(z.object({ experimentId: z.string() }))
    .query(async ({ ctx, input }) => {
      await assertExperimentMembership(ctx.prisma, input.experimentId, ctx.user!.id);

      return ctx.prisma.iteration.findMany({
        where: { experimentId: input.experimentId },
        orderBy: { number: 'desc' },
        take: 20,
        select: {
          id: true,
          number: true,
          status: true,
          startedAt: true,
          finishedAt: true,
          metrics: true,
          totalCost: true,
          totalTokens: true,
        },
      });
    }),

  get: protectedProcedure
    .input(z.object({ iterationId: z.string() }))
    .query(async ({ ctx, input }) => {
      const iteration = await ctx.prisma.iteration.findUnique({
        where: { id: input.iterationId },
        include: {
          experiment: { select: { id: true, projectId: true, name: true } },
          promptVersion: true,
          modelRuns: {
            include: {
              modelConfig: true,
              outputs: { include: { case: true, judgments: true } },
            },
          },
        },
      });

      if (!iteration) {
        throw new Error('Iteration not found');
      }

      await assertExperimentMembership(ctx.prisma, iteration.experiment.id, ctx.user!.id);
      return iteration;
    }),

  outputs: protectedProcedure
    .input(
      z.object({
        iterationId: z.string(),
        cursor: z.string().optional(),
        limit: z.number().int().min(1).max(100).default(25),
      }),
    )
    .query(async ({ ctx, input }) => {
      const iteration = await ctx.prisma.iteration.findUnique({
        where: { id: input.iterationId },
        select: { experimentId: true },
      });

      if (!iteration) {
        throw new Error('Iteration not found');
      }

      await assertExperimentMembership(ctx.prisma, iteration.experimentId, ctx.user!.id);

      const outputs = await ctx.prisma.output.findMany({
        where: { modelRun: { iterationId: input.iterationId } },
        include: { case: true, judgments: true },
        orderBy: { createdAt: 'desc' },
        take: input.limit + 1,
        ...(input.cursor ? { cursor: { id: input.cursor }, skip: 1 } : {}),
      });

      const nextCursor = outputs.length > input.limit ? outputs.pop()?.id ?? null : null;

      return { outputs, nextCursor };
    }),
});
