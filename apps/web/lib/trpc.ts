'use client';

import type { AppRouter } from '@edison/api/src/trpc/router';
import { createTRPCReact } from '@trpc/react-query';

export const trpc = createTRPCReact<AppRouter>();
