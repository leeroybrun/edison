import { ModelParamsSchema, PromptSchema, RubricSchema, StopRulesSchema } from '@edison/shared';
import { JudgeMode, LLMProvider } from '@prisma/client';
import { TRPCError } from '@trpc/server';
import { z } from 'zod';

import { protectedProcedure, router } from '../context';
import { assertProjectMembership } from '../utils/authorization';
import { asJsonObject, asJsonValue } from '../../lib/json';

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

const CreateExperimentInputSchema = z.object({
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
});

type CreateExperimentInput = z.infer<typeof CreateExperimentInputSchema>;
type ModelConfigInput = z.infer<typeof ModelConfigInputSchema>;
type JudgeConfigInput = z.infer<typeof JudgeConfigInputSchema>;
type PromptInput = z.infer<typeof PromptInputSchema>;

export const experimentRouter = router({
  create: protectedProcedure
    .input(CreateExperimentInputSchema)
    .mutation(async ({ ctx, input }) => {
      const data = input as CreateExperimentInput;
      await assertProjectMembership(ctx.prisma, data.projectId, ctx.user!.id, ['EDITOR', 'ADMIN', 'OWNER']);

      const datasets = await ctx.prisma.dataset.findMany({
        where: { id: { in: data.datasetIds }, projectId: data.projectId },
        select: { id: true },
      });

      if (datasets.length !== data.datasetIds.length) {
        throw new TRPCError({ code: 'BAD_REQUEST', message: 'One or more datasets are invalid for this project' });
      }

      for (const config of data.modelConfigs) {
        const credential = await ctx.adapterFactory.tryGetCredentialForProject(data.projectId, config.provider);
        if (!credential) {
          throw new TRPCError({ code: 'BAD_REQUEST', message: `Missing credential for ${config.provider}` });
        }

        const adapter = await ctx.adapterFactory.getAdapter(credential, config.modelId);
        await adapter.validateModel(config.params);
      }

      for (const config of data.judgeConfigs) {
        const credential = await ctx.adapterFactory.tryGetCredentialForProject(data.projectId, config.provider);
        if (!credential) {
          throw new TRPCError({ code: 'BAD_REQUEST', message: `Missing credential for judge provider ${config.provider}` });
        }

        const adapter = await ctx.adapterFactory.getAdapter(credential, config.modelId);
        await adapter.validateModel();
      }

      const promptInput: PromptInput = data.prompt;
      const experiment = await ctx.prisma.experiment.create({
        data: {
          projectId: data.projectId,
          name: data.name,
          description: data.description,
          goal: data.goal,
          rubric: asJsonValue(data.rubric),
          stopRules: asJsonValue(data.stopRules),
          selectorConfig: asJsonObject({ datasetIds: data.datasetIds }),
          promptVersions: {
            create: {
              version: 1,
              text: promptInput.text,
              systemText: promptInput.systemText,
              fewShots: promptInput.fewShots ? asJsonValue(promptInput.fewShots) : undefined,
              toolsSchema: promptInput.toolsSchema ? asJsonValue(promptInput.toolsSchema) : undefined,
              metadata: asJsonObject({ name: promptInput.name }),
              createdBy: ctx.user!.id,
            },
          },
          modelConfigs: {
            create: data.modelConfigs.map((config: ModelConfigInput) => ({
              provider: config.provider,
              modelId: config.modelId,
              params: config.params ? asJsonValue(config.params) : asJsonObject({}),
              seed: config.seed,
            })),
          },
          judgeConfigs: {
            create: data.judgeConfigs.map((config: JudgeConfigInput) => ({
              provider: config.provider,
              modelId: config.modelId,
              mode: config.mode,
              systemPrompt: config.systemPrompt,
            })),
          },
        },
      });

      await ctx.auditLogger.record({
        userId: ctx.user!.id,
        action: 'experiment.create',
        entityType: 'experiment',
        entityId: experiment.id,
        metadata: { projectId: data.projectId },
      });

      return experiment;
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
