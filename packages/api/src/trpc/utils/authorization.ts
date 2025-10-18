import type { PrismaClient, UserRole } from '@prisma/client';
import { TRPCError } from '@trpc/server';

export async function assertProjectMembership(
  prisma: PrismaClient,
  projectId: string,
  userId: string,
  roles?: UserRole[],
): Promise<void> {
  const membership = await prisma.projectMember.findFirst({
    where: {
      projectId,
      userId,
      ...(roles ? { role: { in: roles } } : {}),
    },
  });

  if (!membership) {
    throw new TRPCError({ code: 'FORBIDDEN' });
  }
}

export async function assertExperimentMembership(
  prisma: PrismaClient,
  experimentId: string,
  userId: string,
  roles?: UserRole[],
): Promise<string> {
  const experiment = await prisma.experiment.findUnique({
    where: { id: experimentId },
    select: { projectId: true },
  });

  if (!experiment) {
    throw new TRPCError({ code: 'NOT_FOUND' });
  }

  await assertProjectMembership(prisma, experiment.projectId, userId, roles);
  return experiment.projectId;
}
