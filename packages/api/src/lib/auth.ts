import type { User } from '@prisma/client';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';

import { getConfig } from './config';
import { prisma } from './prisma';

type JwtPayload = {
  sub: string;
  email?: string;
};

export async function authenticate(authorization?: string): Promise<User | null> {
  if (!authorization) {
    return null;
  }

  const [scheme, token] = authorization.split(' ');
  if (scheme?.toLowerCase() !== 'bearer' || !token) {
    return null;
  }

  const config = getConfig();
  try {
    const decoded = jwt.verify(token, config.JWT_SECRET) as JwtPayload;
    if (!decoded.sub) {
      return null;
    }

    const user = await prisma.user.findUnique({ where: { id: decoded.sub } });
    return user;
  } catch (error) {
    return null;
  }
}

export async function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, 12);
}

export async function verifyPassword(plain: string, hashed: string): Promise<boolean> {
  return bcrypt.compare(plain, hashed);
}

export function issueToken(user: User): string {
  const config = getConfig();
  return jwt.sign({ sub: user.id, email: user.email }, config.JWT_SECRET, {
    expiresIn: '7d',
  });
}
