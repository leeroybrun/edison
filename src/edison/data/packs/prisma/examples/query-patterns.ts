import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

export async function listItems(page = 1, pageSize = 20) {
  return prisma.item.findMany({
    select: { id: true, name: true, createdAt: true },
    orderBy: { createdAt: 'desc' },
    skip: (page - 1) * pageSize,
    take: pageSize,
  });
}

