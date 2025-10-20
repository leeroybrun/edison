import { ReviewDecision, SuggestionStatus } from '@prisma/client';
import { z } from 'zod';

import { applyUnifiedDiff } from '../../services/diff-utils';
import { asNullableJson } from '../../lib/json';
import { protectedProcedure, router } from '../context';
import { assertExperimentMembership } from '../utils/authorization';

const ReviewSuggestionInput = z.object({
  suggestionId: z.string(),
  decision: z.nativeEnum(ReviewDecision),
  notes: z.string().max(1000).optional(),
});

export const reviewRouter = router({
  listSuggestions: protectedProcedure
    .input(z.object({ experimentId: z.string() }))
    .query(async ({ ctx, input }) => {
      await assertExperimentMembership(ctx.prisma, input.experimentId, ctx.user!.id);

      return ctx.prisma.suggestion.findMany({
        where: { promptVersion: { experimentId: input.experimentId }, status: 'PENDING' },
        orderBy: { createdAt: 'desc' },
        include: {
          promptVersion: { select: { id: true, version: true, text: true } },
        },
      });
    }),

  reviewSuggestion: protectedProcedure
    .input(ReviewSuggestionInput)
    .mutation(async ({ ctx, input }) => {
      const suggestion = await ctx.prisma.suggestion.findUnique({
        where: { id: input.suggestionId },
        include: {
          promptVersion: {
            include: { experiment: true },
          },
        },
      });

      if (!suggestion) {
        throw new Error('Suggestion not found');
      }

      await assertExperimentMembership(ctx.prisma, suggestion.promptVersion.experimentId, ctx.user!.id, [
        'REVIEWER',
        'EDITOR',
        'ADMIN',
        'OWNER',
      ]);

      return ctx.prisma.$transaction(async (tx) => {
        let appliedVersionId: string | null = null;

        if (input.decision === 'APPROVE') {
          const latestVersion = await tx.promptVersion.findFirst({
            where: { experimentId: suggestion.promptVersion.experimentId },
            orderBy: { version: 'desc' },
          });

          const updatedText = applyUnifiedDiff(suggestion.promptVersion.text, suggestion.diffUnified);

          const newVersion = await tx.promptVersion.create({
            data: {
              experimentId: suggestion.promptVersion.experimentId,
              version: (latestVersion?.version ?? suggestion.promptVersion.version) + 1,
              parentId: suggestion.promptVersionId,
              text: updatedText,
              systemText: suggestion.promptVersion.systemText,
              fewShots: asNullableJson(suggestion.promptVersion.fewShots),
              toolsSchema: asNullableJson(suggestion.promptVersion.toolsSchema),
              changelog: suggestion.note ?? 'Automated refinement applied.',
              createdBy: ctx.user!.id,
            },
          });

          appliedVersionId = newVersion.id;

          await tx.suggestion.update({
            where: { id: suggestion.id },
            data: { status: SuggestionStatus.APPLIED },
          });
        } else if (input.decision === 'REJECT') {
          await tx.suggestion.update({
            where: { id: suggestion.id },
            data: { status: SuggestionStatus.REJECTED },
          });
        }

        await tx.review.create({
          data: {
            suggestionId: suggestion.id,
            reviewerId: ctx.user!.id,
            decision: input.decision,
            notes: input.notes,
          },
        });

        return { suggestionId: suggestion.id, appliedVersionId };
      });
    }),
});
