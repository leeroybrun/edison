# component-builder overlay for Motion pack

<!-- EXTEND: Tools -->
- Motion 12+ for animations: `import { motion, AnimatePresence } from 'motion/react'`
- React 19 with TypeScript for components
- Gesture support via motion props: drag, whileHover, whileTap
- Variants for reusable animations
<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->
- Use AnimatePresence for mount/unmount animations with meaningful exit states
- Prefer layout animations with layout prop over manual positioning
- Implement gesture handling (drag, hover) for interactive feedback
- Define and reuse variants for complex animations
- Optimize animations with GPU-accelerated transforms (x, y, rotate, opacity, scale)
- Memoize animated components to prevent unnecessary re-renders
<!-- /EXTEND -->

<!-- NEW_SECTION: MotionComponentPatterns -->
## AnimatePresence Pattern

When components mount/unmount, use AnimatePresence for smooth transitions:

```tsx
import { AnimatePresence, motion } from 'motion/react'

export function NotificationList({ notifications }) {
  return (
    <AnimatePresence mode="popLayout">
      {notifications.map(notification => (
        <motion.div
          key={notification.id}
          initial={{ opacity: 0, x: -100 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -100 }}
          transition={{ duration: 0.2 }}
        >
          {notification.message}
        </motion.div>
      ))}
    </AnimatePresence>
  )
}
```

**Key Points**:
- Wrap all dynamic lists with AnimatePresence
- Always define exit animation
- Use `mode="popLayout"` for better performance
- Unique keys required for proper animations

---

## Layout Animation Pattern

Use layout animations for position/size changes without measuring DOM:

```tsx
export function ResponsiveGrid({ items }) {
  return (
    <div className="grid">
      {items.map(item => (
        <motion.div
          key={item.id}
          layout  // Animate position/size changes
          transition={{ duration: 0.3 }}
          className="grid-item"
        >
          {item.content}
        </motion.div>
      ))}
    </div>
  )
}
```

**Key Points**:
- Add layout prop to reflow animations
- Use layoutId for shared element transitions
- Much cheaper than measuring DOM manually

---

## Gesture Handling Pattern

Create responsive interactions with drag and hover:

```tsx
export function DraggableCard({ onClose }) {
  return (
    <motion.div
      drag
      dragConstraints={{ left: -20, right: 20, top: -20, bottom: 20 }}
      dragElastic={0.2}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onDragEnd={(event, info) => {
        if (Math.abs(info.offset.x) > 100) onClose()
      }}
      className="card"
    >
      {content}
    </motion.div>
  )
}
```

**Key Points**:
- Always set dragConstraints
- Provide dragElastic for spring-like feel
- Use whileHover/whileTap for feedback
- Handle onDragEnd for logic triggers

---

## Variants Pattern

Define and reuse animations consistently:

```tsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
}

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: { y: 0, opacity: 1 },
}

export function List({ items }) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {items.map(item => (
        <motion.div key={item.id} variants={itemVariants}>
          {item.name}
        </motion.div>
      ))}
    </motion.div>
  )
}
```

**Key Points**:
- Extract variants to objects for reusability
- Use staggerChildren for orchestrated animations
- Named states (hidden, visible, error) for clarity

---

## Performance Optimization Pattern

Keep animations smooth at 60fps:

```tsx
import { memo } from 'react'
import { motion } from 'motion/react'

// Memoize animated components
const AnimatedItem = memo(function AnimatedItem({ item }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      // Only animate transforms and opacity (GPU-accelerated)
      transition={{ duration: 0.3 }}
    >
      {item.content}
    </motion.div>
  )
})

export function List({ items }) {
  return (
    <div>
      {items.map(item => (
        <AnimatedItem key={item.id} item={item} />
      ))}
    </div>
  )
}
```

**Key Points**:
- Use memo() for animated list items
- Animate only x, y, rotate, opacity, scale
- Avoid width, height, padding, etc.
- Add willChange for complex animations
- Keep animations under 500ms for UI feedback

