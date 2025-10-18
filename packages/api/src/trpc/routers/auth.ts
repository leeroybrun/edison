import { randomUUID } from 'crypto';

import type { PrismaClient } from '@prisma/client';
import { TRPCError } from '@trpc/server';
import { z } from 'zod';

import { hashPassword, issueToken, verifyPassword } from '../../lib/auth';
import { protectedProcedure, publicProcedure, router } from '../context';

function slugify(base: string): string {
  const normalized = base
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 32);
  return `${normalized || 'workspace'}-${randomUUID().slice(0, 8)}`;
}

async function ensureUniqueProjectSlug(prisma: PrismaClient, slug: string): Promise<string> {
  let attempt = slug;
  let counter = 1;
  let collision = true;

  while (collision) {
    const existing = await prisma.project.findUnique({ where: { slug: attempt } });
    if (!existing) {
      collision = false;
    } else {
      attempt = `${slug}-${counter}`;
      counter += 1;
    }
  }

  return attempt;
}

export const authRouter = router({
  register: publicProcedure
    .input(
      z.object({
        email: z.string().email(),
        password: z.string().min(10),
        name: z.string().min(2).max(100),
        workspaceName: z.string().min(2).max(100).optional(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const existing = await ctx.prisma.user.findUnique({ where: { email: input.email } });
      if (existing) {
        throw new TRPCError({ code: 'CONFLICT', message: 'User already exists' });
      }

      const passwordHash = await hashPassword(input.password);

      const result = await ctx.prisma.$transaction(async (tx) => {
        const user = await tx.user.create({
          data: {
            email: input.email,
            name: input.name,
            passwordHash,
            role: 'OWNER',
          },
        });

        const slugBase = slugify(input.workspaceName ?? input.name ?? input.email.split('@')[0]);
        const slug = await ensureUniqueProjectSlug(tx, slugBase);
        const project = await tx.project.create({
          data: {
            name: input.workspaceName ?? `${input.name}'s Workspace`,
            slug,
            description: 'Personal workspace created during registration',
          },
        });

        await tx.projectMember.create({
          data: {
            projectId: project.id,
            userId: user.id,
            role: 'OWNER',
          },
        });

        return { user, project };
      });

      const token = issueToken(result.user);

      await ctx.auditLogger.record({
        userId: result.user.id,
        action: 'auth.register',
        entityType: 'user',
        entityId: result.user.id,
        metadata: { projectId: result.project.id },
      });

      return {
        token,
        user: {
          id: result.user.id,
          email: result.user.email,
          name: result.user.name,
        },
        project: {
          id: result.project.id,
          slug: result.project.slug,
          name: result.project.name,
        },
      };
    }),
  login: publicProcedure
    .input(
      z.object({
        email: z.string().email(),
        password: z.string().min(1),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      await ctx.rateLimiter.consume({ key: `login:${input.email}`, limit: 10, windowMs: 10 * 60 * 1000 });

      const user = await ctx.prisma.user.findUnique({
        where: { email: input.email },
        include: {
          projects: {
            include: { project: true },
          },
        },
      });

      if (!user) {
        await ctx.auditLogger.record({
          userId: null,
          action: 'auth.login.failed',
          entityType: 'user',
          entityId: input.email,
          metadata: { reason: 'not_found' },
        });
        throw new TRPCError({ code: 'UNAUTHORIZED', message: 'Invalid credentials' });
      }

      const valid = await verifyPassword(input.password, user.passwordHash);
      if (!valid) {
        await ctx.auditLogger.record({
          userId: user.id,
          action: 'auth.login.failed',
          entityType: 'user',
          entityId: user.id,
          metadata: { reason: 'invalid_password' },
        });
        throw new TRPCError({ code: 'UNAUTHORIZED', message: 'Invalid credentials' });
      }

      const token = issueToken(user);

      await ctx.auditLogger.record({
        userId: user.id,
        action: 'auth.login',
        entityType: 'user',
        entityId: user.id,
        metadata: { projectIds: user.projects.map((member) => member.projectId) },
      });

      return {
        token,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
        },
        projects: user.projects.map((member) => ({
          id: member.project.id,
          slug: member.project.slug,
          name: member.project.name,
          role: member.role,
        })),
      };
    }),
  me: protectedProcedure.query(async ({ ctx }) => {
    const user = await ctx.prisma.user.findUnique({
      where: { id: ctx.user!.id },
      include: {
        projects: {
          include: { project: true },
        },
      },
    });

    if (!user) {
      throw new TRPCError({ code: 'NOT_FOUND' });
    }

    return {
      id: user.id,
      email: user.email,
      name: user.name,
      projects: user.projects.map((member) => ({
        id: member.project.id,
        slug: member.project.slug,
        name: member.project.name,
        role: member.role,
      })),
    };
  }),
});
