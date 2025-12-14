# Performance

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Avoid animating layout properties when possible; prefer transforms and opacity.
- Keep animated lists small; virtualize if needed.
- Avoid re-creating objects every render for hot paths (variants, transitions).

```tsx
import { motion } from 'motion/react'

export function FadeIn({ children }: { children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.15 }}>
      {children}
    </motion.div>
  )
}
```
<!-- /section: patterns -->
