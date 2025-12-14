# Variants

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Use variants to keep state-driven animations consistent across components.
- Prefer a small number of variants with clear names.

```tsx
import { motion } from 'motion/react'

const variants = {
  closed: { opacity: 0, y: 8 },
  open: { opacity: 1, y: 0 },
}

export function Disclosure({ open }: { open: boolean }) {
  return <motion.div variants={variants} animate={open ? 'open' : 'closed'} />
}
```
<!-- /section: patterns -->
