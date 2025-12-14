# Animate Presence

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Use `AnimatePresence` for enter/exit transitions when components unmount.
- Provide stable `key`s; exit animations depend on them.
- Keep exit animations short; avoid blocking navigation.

```tsx
import { AnimatePresence, motion } from 'motion/react'

export function Panel({ isOpen }: { isOpen: boolean }) {
  return (
    <AnimatePresence>
      {isOpen ? (
        <motion.div
          key="panel"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 8 }}
        />
      ) : null}
    </AnimatePresence>
  )
}
```
<!-- /section: patterns -->
