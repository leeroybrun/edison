# component-builder-nextjs (Next.js 16)

## Tools
- Next.js 16 App Router components in `apps/dashboard/src/app/**`.
- React Server/Client Components with strict TypeScript.
- `pnpm lint --filter dashboard` and `pnpm test --filter dashboard`.

## Guidelines
- Default to Server Components; mark `"use client"` only when needed (state, effects, event handlers).
- Keep data fetching in Server Components; pass serialized props to clients.
- Use Next.js conventions: file-based routing, `route.ts` API proxies, metadata exports, and `next/image` for assets.
- Co-locate loading/error states with routes; avoid client-only data fetching unless required.
- Align with design system classes; prefer shared utilities from `@/lib/*`.
