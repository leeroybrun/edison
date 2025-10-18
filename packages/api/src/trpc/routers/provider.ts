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
        where: { projectId: input.projectId, deletedAt: null },
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
        // Prisma client does not yet expose the soft-delete field in generated types in this workspace.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data: (
          {
            projectId: input.projectId,
            provider: input.provider,
            label: input.label,
            encryptedApiKey,
            config: input.config ?? {},
            deletedAt: null,
          }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ) as any,
      });

      await ctx.auditLogger.record({
        userId: ctx.user!.id,
        action: 'provider.create',
        entityType: 'providerCredential',
        entityId: credential.id,
        metadata: { provider: credential.provider },
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

      if ((credential as { deletedAt?: Date | null }).deletedAt) {
        throw new Error('Credential has been archived and cannot be modified');
      }

      await assertProjectMembership(ctx.prisma, credential.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      const updated = await ctx.prisma.providerCredential.update({
        where: { id: input.credentialId },
        data: { isActive: input.isActive },
        select: { id: true, isActive: true },
      });

      await ctx.auditLogger.record({
        userId: ctx.user!.id,
        action: 'provider.toggle',
        entityType: 'providerCredential',
        entityId: input.credentialId,
        metadata: { isActive: input.isActive },
      });

      return updated;
    }),

  remove: protectedProcedure
    .input(DeleteCredentialInput)
    .mutation(async ({ ctx, input }) => {
      const credential = await ctx.prisma.providerCredential.findUnique({ where: { id: input.credentialId } });
      if (!credential) {
        throw new Error('Credential not found');
      }

      await assertProjectMembership(ctx.prisma, credential.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      await ctx.prisma.providerCredential.update({
        where: { id: input.credentialId },
        data: (
          { deletedAt: new Date(), isActive: false }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ) as any,
      });

      await ctx.auditLogger.record({
        userId: ctx.user!.id,
        action: 'provider.archive',
        entityType: 'providerCredential',
        entityId: input.credentialId,
      });

      return { id: input.credentialId };
    }),
});
