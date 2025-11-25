# App Router Structure

- Organize routes under `app/` using nested folders, `page.tsx`, and `layout.tsx`.
- Co-locate loading and error UI with `loading.tsx` and `error.tsx`.
- In Next.js 16 App Router, prefer Server Components by default; mark Client Components with `'use client'` only when strictly necessary.
