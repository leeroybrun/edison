import { Prisma } from '@prisma/client';

export function asJsonValue(value: unknown): Prisma.InputJsonValue {
  return value as Prisma.InputJsonValue;
}

export function asJsonObject(value?: Record<string, unknown> | null): Prisma.JsonObject {
  return (value ?? {}) as Prisma.JsonObject;
}

export function asNullableJson(value?: unknown): Prisma.InputJsonValue | typeof Prisma.JsonNull | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return Prisma.JsonNull;
  }
  return value as Prisma.InputJsonValue;
}
