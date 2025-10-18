import { LLMProvider } from '@prisma/client';
import { z } from 'zod';

import { encrypt } from '../../lib/crypto';
import { protectedProcedure, router } from '../context';
import { assertProjectMembership } from '../utils/authorization';

const CreateCredentialInput = z.object({
  projectId: z.string(),
  provider: z.nativeEnum(LLMProvider),
  label: z.string().min(1).max(50),
  apiKey: z.string().min(1).optional(),
  config: z.record(z.unknown()).optional(),
});

const ToggleCredentialInput = z.object({
  credentialId: z.string(),
  isActive: z.boolean(),
});

const DeleteCredentialInput = z.object({
  credentialId: z.string(),
});

export const providerRouter = router({
  list: protectedProcedure
    .input(z.object({ projectId: z.string() }))
    .query(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id);

      return ctx.prisma.providerCredential.findMany({
        where: { projectId: input.projectId },
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          provider: true,
          label: true,
          isActive: true,
          config: true,
          createdAt: true,
        },
      });
    }),

  create: protectedProcedure
    .input(CreateCredentialInput)
    .mutation(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      const encryptedApiKey = await encrypt(input.apiKey ?? '');
      const credential = await ctx.prisma.providerCredential.create({
        data: {
          projectId: input.projectId,
          provider: input.provider,
          label: input.label,
          encryptedApiKey,
          config: input.config ?? {},
        },
      });

      return {
        id: credential.id,
        provider: credential.provider,
        label: credential.label,
        isActive: credential.isActive,
        config: credential.config,
      };
    }),

  toggle: protectedProcedure
    .input(ToggleCredentialInput)
    .mutation(async ({ ctx, input }) => {
      const credential = await ctx.prisma.providerCredential.findUnique({ where: { id: input.credentialId } });
      if (!credential) {
        throw new Error('Credential not found');
      }

      await assertProjectMembership(ctx.prisma, credential.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      return ctx.prisma.providerCredential.update({
        where: { id: input.credentialId },
        data: { isActive: input.isActive },
        select: { id: true, isActive: true },
      });
    }),

  remove: protectedProcedure
    .input(DeleteCredentialInput)
    .mutation(async ({ ctx, input }) => {
      const credential = await ctx.prisma.providerCredential.findUnique({ where: { id: input.credentialId } });
      if (!credential) {
        throw new Error('Credential not found');
      }

      await assertProjectMembership(ctx.prisma, credential.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      await ctx.prisma.providerCredential.delete({ where: { id: input.credentialId } });
      return { id: input.credentialId };
    }),
});
