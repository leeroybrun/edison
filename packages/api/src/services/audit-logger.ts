import type { PrismaClient } from '@prisma/client';

export interface AuditLogOptions {
  userId?: string | null;
  action: string;
  entityType: string;
  entityId: string;
  changes?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
}

export class AuditLogger {
  constructor(private readonly prisma: PrismaClient) {}

  async record(options: AuditLogOptions): Promise<void> {
    await this.prisma.auditLog.create({
      data: {
        userId: options.userId ?? null,
        action: options.action,
        entityType: options.entityType,
        entityId: options.entityId,
        changes: options.changes ?? null,
        metadata: options.metadata ?? {},
      },
    });
  }
}
