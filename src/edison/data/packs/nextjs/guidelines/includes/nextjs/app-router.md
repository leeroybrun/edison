# App Router Structure

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Organize routes under `app/` using nested folders, `page.tsx`, and `layout.tsx`.
- Co-locate loading and error UI with `loading.tsx` and `error.tsx`.
- In Next.js 16 App Router, prefer Server Components by default; mark Client Components with `'use client'` only when strictly necessary.
<!-- /section: patterns -->
