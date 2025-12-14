# Layout Animations

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Prefer layout animations for reordering / resizing lists.
- Use `layout` for simple cases; consider `layoutId` for shared element transitions.

```tsx
import { motion } from 'motion/react'

export function Card({ children }: { children: React.ReactNode }) {
  return (
    <motion.div layout className="card">
      {children}
    </motion.div>
  )
}
```
<!-- /section: patterns -->
