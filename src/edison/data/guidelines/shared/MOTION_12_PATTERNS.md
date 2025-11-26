# Motion 12 Animation Patterns

## Overview
This guideline establishes the standard patterns for using Motion 12 (formerly Framer Motion) within the Edison project. Motion 12 provides a declarative API for animations, gestures, and layout transitions in React applications.

We use the unified `motion/react` entry point introduced in Motion 12.

## Basic Animations
Basic animations are achieved using the `motion` component and the `initial` and `animate` props.

```tsx
import { motion } from 'motion/react';

export function SimpleFade() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      Hello
    </motion.div>
  );
}

export function FadeInComponent() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      Content
    </motion.div>
  );
}
```

## Variants
Use variants to orchestrate animations across multiple components, allowing for staggered children animations.

```tsx
const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
};

export function List() {
  return (
    <motion.ul
      variants={container}
      initial="hidden"
      animate="show"
    >
      <motion.li variants={item}>Item 1</motion.li>
      <motion.li variants={item}>Item 2</motion.li>
    </motion.ul>
  );
}
```

## AnimatePresence
Use `AnimatePresence` to animate components when they are removed from the React tree.

```tsx
import { AnimatePresence, motion } from 'motion/react';

export function Notification({ isVisible }: { isVisible: boolean }) {
  return (
    <AnimatePresence mode="wait">
      {isVisible && (
        <motion.div
          key="notification"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
        >
          Notification
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

## Layout Animations
Motion can automatically animate layout changes using the `layout` prop. Use `layoutId` for shared element transitions.

```tsx
// Automatic layout animation
<motion.div layout>
  {/* content that changes size */}
</motion.div>

// Shared element transition
<motion.div layoutId="underline" className="underline" />
```

## Gestures
Motion provides simple props for handling gestures like hover, tap, and drag.

```tsx
<motion.button
  whileHover={{ scale: 1.1 }}
  whileTap={{ scale: 0.95 }}
  drag
  dragConstraints={{ left: 0, right: 100 }}
>
  Click Me
</motion.button>
```

## Scroll Animations
Use `useScroll` and `useTransform` for scroll-linked animations.

```tsx
import { motion, useScroll, useTransform } from 'motion/react';

export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return <motion.div style={{ scaleX }} />;
}
```

## Best Practices

### Performance
- **Hardware Acceleration**: Use `transform` and `opacity` for smooth 60fps animations. Avoid animating layout properties (width, height, top, left) continuously.
- **Will-Change**: Use the `will-change` CSS property sparingly for complex animations to hint the browser.
- **Lazy Motion**: For large bundles, consider using `LazyMotion` to load animation features on demand.
- **DOM Animation**: If size is critical and you only need basic animations, use the `domAnimation` feature subset.
- **Reduce Layout Thrashing**: When using `layout` animations, ensure parent containers have fixed dimensions if possible to avoid expensive recalculations.

### Accessibility
- Respect `prefers-reduced-motion`. Motion handles this by default, but ensure complex animations can be disabled.
- Ensure animations do not cause dizziness or nausea (avoid excessive parallax or scaling).

### Imports
- **ALWAYS** import from `'motion/react'`.
- **NEVER** import from `'framer-motion'` (legacy).
