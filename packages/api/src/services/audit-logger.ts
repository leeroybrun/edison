import type { PrismaClient } from '@prisma/client';

import { asJsonObject, asNullableJson } from '../lib/json';

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
        changes: asNullableJson(options.changes),
        metadata: asJsonObject(options.metadata ?? {}),
      },
    });
  }
}
