import { RubricSchema } from '@edison/shared';
import { z } from 'zod';

import { protectedProcedure, router } from '../context';
import { assertProjectMembership } from '../utils/authorization';

export const aiAssistRouter = router({
  draftObjective: protectedProcedure
    .input(
      z.object({
        hints: z.string().min(10).max(500),
        count: z.number().int().min(1).max(5).default(3),
        projectId: z.string().optional(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      return ctx.aiAssist.draftObjectives(input.hints, input.count, input.projectId);
    }),

  draftRubric: protectedProcedure
    .input(z.object({ objective: z.string().min(10), projectId: z.string().optional() }))
    .mutation(async ({ ctx, input }) => ctx.aiAssist.draftRubric(input.objective, input.projectId)),

  draftPrompts: protectedProcedure
    .input(
      z.object({
        objective: z.string().min(10),
        rubric: RubricSchema,
        count: z.number().int().min(1).max(5).default(3),
        projectId: z.string().optional(),
      }),
    )
    .mutation(async ({ ctx, input }) =>
      ctx.aiAssist.draftPrompts(input.objective, input.rubric, input.count, input.projectId),
    ),

  improvePrompt: protectedProcedure
    .input(
      z.object({
        promptText: z.string().min(10),
        objective: z.string().min(10),
        focus: z.array(z.string()).optional(),
        projectId: z.string().optional(),
      }),
    )
    .mutation(async ({ ctx, input }) =>
      ctx.aiAssist.improvePrompt({ text: input.promptText }, input.objective, input.focus, input.projectId),
    ),

  generateSynthetic: protectedProcedure
    .input(
      z.object({
        projectId: z.string(),
        domainHints: z.string().min(10),
        count: z.number().int().min(10).max(500),
        diversity: z.number().min(0).max(1),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id, ['EDITOR', 'ADMIN', 'OWNER']);

      const datasetId = await ctx.generator.generateSyntheticDataset(input.projectId, {
        count: input.count,
        diversity: input.diversity,
        domainHints: input.domainHints,
      });

      return { datasetId };
    }),
});
