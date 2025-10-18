import type { UserRole } from '@prisma/client';
import { UserRole as UserRoleEnum } from '@prisma/client';
import { TRPCError } from '@trpc/server';
import { z } from 'zod';

import { protectedProcedure, router } from '../context';
import { assertProjectMembership } from '../utils/authorization';

const CreateProjectInput = z.object({
  name: z.string().min(2).max(100),
  description: z.string().max(500).optional(),
});

const UpdateProjectInput = z.object({
  projectId: z.string(),
  name: z.string().min(2).max(100).optional(),
  description: z.string().max(500).optional(),
  settings: z.record(z.unknown()).optional(),
});

const InviteMemberInput = z.object({
  projectId: z.string(),
  email: z.string().email(),
  role: z.nativeEnum(UserRoleEnum),
});

const UpdateMemberRoleInput = z.object({
  projectId: z.string(),
  userId: z.string(),
  role: z.nativeEnum(UserRoleEnum),
});

const RemoveMemberInput = z.object({
  projectId: z.string(),
  userId: z.string(),
});

export const projectRouter = router({
  list: protectedProcedure.query(async ({ ctx }) => {
    const memberships = await ctx.prisma.projectMember.findMany({
      where: { userId: ctx.user!.id },
      include: { project: true },
      orderBy: { createdAt: 'desc' },
    });

    return memberships.map((membership) => ({
      id: membership.project.id,
      slug: membership.project.slug,
      name: membership.project.name,
      description: membership.project.description,
      role: membership.role,
    }));
  }),

  get: protectedProcedure
    .input(z.object({ projectId: z.string() }))
    .query(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id);

      return ctx.prisma.project.findUniqueOrThrow({
        where: { id: input.projectId },
        include: {
          members: { include: { user: { select: { id: true, email: true, name: true } } } },
          datasets: { select: { id: true, name: true, kind: true } },
        },
      });
    }),

  create: protectedProcedure
    .input(CreateProjectInput)
    .mutation(async ({ ctx, input }) => {
      const project = await ctx.prisma.project.create({
        data: {
          name: input.name,
          description: input.description,
          slug: `${input.name.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}-${Date.now().toString(36)}`.slice(0, 48),
          members: {
            create: {
              userId: ctx.user!.id,
              role: 'OWNER',
            },
          },
        },
      });

      return project;
    }),

  update: protectedProcedure
    .input(UpdateProjectInput)
    .mutation(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      return ctx.prisma.project.update({
        where: { id: input.projectId },
        data: {
          ...(input.name ? { name: input.name } : {}),
          ...(input.description ? { description: input.description } : {}),
          ...(input.settings ? { settings: input.settings } : {}),
        },
      });
    }),

  inviteMember: protectedProcedure
    .input(InviteMemberInput)
    .mutation(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      const user = await ctx.prisma.user.findUnique({ where: { email: input.email } });
      if (!user) {
        throw new TRPCError({ code: 'NOT_FOUND', message: 'User not found' });
      }

      await ctx.prisma.projectMember.upsert({
        where: { projectId_userId: { projectId: input.projectId, userId: user.id } },
        update: { role: input.role as UserRole },
        create: { projectId: input.projectId, userId: user.id, role: input.role as UserRole },
      });

      return { userId: user.id, role: input.role };
    }),

  updateMemberRole: protectedProcedure
    .input(UpdateMemberRoleInput)
    .mutation(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      if (ctx.user!.id === input.userId && input.role !== 'OWNER') {
        throw new TRPCError({ code: 'BAD_REQUEST', message: 'Owners cannot demote themselves' });
      }

      await ctx.prisma.projectMember.update({
        where: { projectId_userId: { projectId: input.projectId, userId: input.userId } },
        data: { role: input.role as UserRole },
      });

      return { userId: input.userId, role: input.role };
    }),

  removeMember: protectedProcedure
    .input(RemoveMemberInput)
    .mutation(async ({ ctx, input }) => {
      await assertProjectMembership(ctx.prisma, input.projectId, ctx.user!.id, ['ADMIN', 'OWNER']);

      if (ctx.user!.id === input.userId) {
        throw new TRPCError({ code: 'BAD_REQUEST', message: 'Cannot remove yourself from the project' });
      }

      await ctx.prisma.projectMember.delete({
        where: { projectId_userId: { projectId: input.projectId, userId: input.userId } },
      });

      return { userId: input.userId };
    }),
});
