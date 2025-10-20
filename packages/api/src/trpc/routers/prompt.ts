import type { PrismaClient, UserRole } from '@prisma/client';
import { TRPCError } from '@trpc/server';
import { parsePatch, applyPatch } from 'diff';
import { z } from 'zod';

import { router, protectedProcedure } from '../context';
import { asJsonValue, asNullableJson } from '../../lib/json';

async function ensureMember(
  prisma: PrismaClient,
  projectId: string,
  userId: string,
  roles?: UserRole[],
) {
  try {
    await prisma.projectMember.findFirstOrThrow({
      where: {
        projectId,
        userId,
        ...(roles ? { role: { in: roles } } : {}),
      },
    });
  } catch (error) {
    throw new TRPCError({ code: 'FORBIDDEN' });
  }
}

export const promptRouter = router({
  createVersion: protectedProcedure
    .input(
      z.object({
        experimentId: z.string(),
        text: z.string().min(10),
        systemText: z.string().optional(),
        fewShots: z.array(z.object({ user: z.string(), assistant: z.string() })).optional(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const experiment = await ctx.prisma.experiment.findUniqueOrThrow({ where: { id: input.experimentId } });
      await ensureMember(ctx.prisma, experiment.projectId, ctx.user!.id, ['EDITOR', 'ADMIN', 'OWNER']);

      const last = await ctx.prisma.promptVersion.findFirst({
        where: { experimentId: input.experimentId },
        orderBy: { version: 'desc' },
      });

      return ctx.prisma.promptVersion.create({
        data: {
          experimentId: input.experimentId,
          version: (last?.version ?? 0) + 1,
          text: input.text,
          systemText: input.systemText,
          fewShots: input.fewShots ? asJsonValue(input.fewShots) : undefined,
          createdBy: ctx.user!.id,
        },
      });
    }),
  applySuggestion: protectedProcedure
    .input(z.object({ suggestionId: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const suggestion = await ctx.prisma.suggestion.findUniqueOrThrow({
        where: { id: input.suggestionId },
        include: { promptVersion: true },
      });

      const experiment = await ctx.prisma.experiment.findUniqueOrThrow({
        where: { id: suggestion.promptVersion.experimentId },
      });
      await ensureMember(ctx.prisma, experiment.projectId, ctx.user!.id, ['EDITOR', 'ADMIN', 'OWNER']);

      const patches = parsePatch(suggestion.diffUnified);
      if (patches.length === 0) {
        throw new Error('Diff payload is empty');
      }

      const updated = applyPatch(suggestion.promptVersion.text, patches[0]);
      if (!updated) {
        throw new Error('Failed to apply diff');
      }

      const newVersion = await ctx.prisma.promptVersion.create({
        data: {
          experimentId: suggestion.promptVersion.experimentId,
          version: suggestion.promptVersion.version + 1,
          parentId: suggestion.promptVersion.id,
          text: updated,
          systemText: suggestion.promptVersion.systemText,
          fewShots: asNullableJson(suggestion.promptVersion.fewShots),
          toolsSchema: asNullableJson(suggestion.promptVersion.toolsSchema),
          changelog: suggestion.note,
          createdBy: ctx.user!.id,
        },
      });

      await ctx.prisma.suggestion.update({
        where: { id: suggestion.id },
        data: { status: 'APPLIED' },
      });

      return newVersion;
    }),
});
