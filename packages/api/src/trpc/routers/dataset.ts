import { z } from 'zod';

import { protectedProcedure, router } from '../context';
import { assertProjectMembership } from '../utils/authorization';

export const datasetRouter = router({
  list: protectedProcedure
    .input(z.object({ projectId: z.string().min(1) }))
    .query(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id);

      return ctx.prisma.dataset.findMany({
        where: { projectId: input.projectId },
        include: { cases: { take: 5 } },
        orderBy: { createdAt: 'desc' },
      });
    }),
  generateSynthetic: protectedProcedure
    .input(
      z.object({
        projectId: z.string(),
        count: z.number().int().min(1).max(200),
        diversity: z.number().min(0).max(1),
        domainHints: z.string().min(10),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id, ['EDITOR', 'ADMIN', 'OWNER']);

      const dataset = await ctx.prisma.dataset.create({
        data: {
          projectId: input.projectId,
          name: `Synthetic ${new Date().toISOString()}`,
          kind: 'SYNTHETIC',
          metadata: {
            status: 'pending',
            spec: {
              count: input.count,
              diversity: input.diversity,
              domainHints: input.domainHints,
            },
          },
        },
      });

      const job = await ctx.queues.generate.add('generate-dataset', {
        datasetId: dataset.id,
        projectId: input.projectId,
        spec: {
          count: input.count,
          diversity: input.diversity,
          domainHints: input.domainHints,
        },
      });

      await ctx.auditLogger.record({
        userId: ctx.user!.id,
        action: 'dataset.generateSynthetic',
        entityType: 'dataset',
        entityId: dataset.id,
        metadata: { jobId: job.id },
      });

      return { datasetId: dataset.id, jobId: job.id };
    }),
});
