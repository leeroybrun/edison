import { ModelParamsSchema, PromptSchema, RubricSchema, StopRulesSchema } from '@edison/shared';
import { JudgeMode, LLMProvider } from '@prisma/client';
import { TRPCError } from '@trpc/server';
import { z } from 'zod';

import { protectedProcedure, router } from '../context';
import { assertProjectMembership } from '../utils/authorization';

const ModelConfigInputSchema = z.object({
  provider: z.nativeEnum(LLMProvider),
  modelId: z.string().min(1),
  params: ModelParamsSchema.partial().optional(),
  seed: z.number().int().optional(),
});

const JudgeConfigInputSchema = z.object({
  provider: z.nativeEnum(LLMProvider),
  modelId: z.string().min(1),
  mode: z.nativeEnum(JudgeMode),
  systemPrompt: z.string().min(10),
});

const PromptInputSchema = PromptSchema.pick({
  name: true,
  systemText: true,
  text: true,
  fewShots: true,
  toolsSchema: true,
});

export const experimentRouter = router({
  create: protectedProcedure
    .input(
      z.object({
        projectId: z.string().min(1),
        name: z.string().min(1).max(200),
        description: z.string().optional(),
        goal: z.string().min(10),
        rubric: RubricSchema,
        stopRules: StopRulesSchema,
        datasetIds: z.array(z.string().min(1)).min(1),
        prompt: PromptInputSchema,
        modelConfigs: z.array(ModelConfigInputSchema).min(1),
        judgeConfigs: z.array(JudgeConfigInputSchema).min(1),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id, ['EDITOR', 'ADMIN', 'OWNER']);

      const datasets = await ctx.prisma.dataset.findMany({
        where: { id: { in: input.datasetIds }, projectId: input.projectId },
        select: { id: true },
      });

      if (datasets.length !== input.datasetIds.length) {
        throw new TRPCError({ code: 'BAD_REQUEST', message: 'One or more datasets are invalid for this project' });
      }

      return ctx.prisma.experiment.create({
        data: {
          projectId: input.projectId,
          name: input.name,
          description: input.description,
          goal: input.goal,
          rubric: input.rubric,
          stopRules: input.stopRules,
          selectorConfig: { datasetIds: input.datasetIds },
          promptVersions: {
            create: {
              version: 1,
              text: input.prompt.text,
              systemText: input.prompt.systemText,
              fewShots: input.prompt.fewShots,
              toolsSchema: input.prompt.toolsSchema,
              metadata: { name: input.prompt.name },
              createdBy: ctx.user!.id,
            },
          },
          modelConfigs: {
            create: input.modelConfigs.map((config) => ({
              provider: config.provider,
              modelId: config.modelId,
              params: config.params ?? {},
              seed: config.seed,
            })),
          },
          judgeConfigs: {
            create: input.judgeConfigs.map((config) => ({
              provider: config.provider,
              modelId: config.modelId,
              mode: config.mode,
              systemPrompt: config.systemPrompt,
            })),
          },
        },
      });
    }),
  listByProject: protectedProcedure
    .input(z.object({ projectId: z.string().min(1) }))
    .query(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id);

      return ctx.prisma.experiment.findMany({
        where: { projectId: input.projectId },
        orderBy: { createdAt: 'desc' },
      });
    }),
  get: protectedProcedure
    .input(z.object({ id: z.string().min(1) }))
    .query(async ({ ctx, input }) => {
      const experiment = await ctx.prisma.experiment.findUnique({
        where: { id: input.id },
        include: {
          promptVersions: { orderBy: { version: 'desc' }, take: 10 },
          iterations: { orderBy: { number: 'desc' }, take: 5 },
        },
      });

      if (!experiment) {
        throw new Error('Experiment not found');
      }

      await assertProjectMembership(ctx.prisma, experiment.projectId, ctx.user!.id);

      return experiment;
    }),
  startIteration: protectedProcedure
    .input(z.object({ experimentId: z.string(), promptVersionId: z.string().optional() }))
    .mutation(async ({ ctx, input }) => {
      const experiment = await ctx.prisma.experiment.findUniqueOrThrow({
        where: { id: input.experimentId },
        include: {
          promptVersions: { orderBy: { version: 'desc' }, take: 1 },
        },
      });

      await assertProjectMembership(ctx.prisma, experiment.projectId, ctx.user!.id, ['EDITOR', 'ADMIN', 'OWNER']);

      const promptVersionId = input.promptVersionId ?? experiment.promptVersions[0]?.id;
      if (!promptVersionId) {
        throw new Error('No prompt version available');
      }

      const iterationId = await ctx.orchestrator.startIteration(experiment.id, promptVersionId);
      return { iterationId };
    }),
});
