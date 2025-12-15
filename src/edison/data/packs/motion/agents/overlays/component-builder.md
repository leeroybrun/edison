# component-builder overlay for Motion pack

<!-- extend: tools -->
- Motion 12+ for animations: `import { motion, AnimatePresence } from 'motion/react'`
- React 19 with TypeScript for components
- Gesture support via motion props: drag, whileHover, whileTap
- Variants for reusable animations
<!-- /extend -->

<!-- extend: guidelines -->
- Use AnimatePresence for mount/unmount animations with meaningful exit states
- Prefer layout animations with layout prop over manual positioning
- Implement gesture handling (drag, hover) for interactive feedback
- Define and reuse variants for complex animations
- Optimize animations with GPU-accelerated transforms (x, y, rotate, opacity, scale)
- Memoize animated components to prevent unnecessary re-renders
- References:
  - `packs/motion/guidelines/includes/motion/animate-presence.md`
  - `packs/motion/guidelines/includes/motion/layout-animations.md`
  - `packs/motion/guidelines/includes/motion/gesture-handling.md`
  - `packs/motion/guidelines/includes/motion/variants-system.md`
  - `packs/motion/guidelines/includes/motion/performance.md`
<!-- /extend -->
