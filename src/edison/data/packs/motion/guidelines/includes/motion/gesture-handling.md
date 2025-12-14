# Gesture Handling

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Use `whileHover`, `whileTap` for simple affordances.
- For drag interactions, constrain and add momentum consciously.

```tsx
import { motion } from 'motion/react'

export function Pressable({ label }: { label: string }) {
  return (
    <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
      {label}
    </motion.button>
  )
}
```
<!-- /section: patterns -->
