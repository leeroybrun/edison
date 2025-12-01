# Gesture Handling

## Overview

Motion provides built-in support for common gestures: drag, hover, tap, and focus. These create responsive, tactile user experiences that feel good.

## Available Gestures

| Gesture | Prop | Use Case |
|---------|------|----------|
| Hover | whileHover | Feedback on pointer over |
| Tap | whileTap | Feedback on click/touch |
| Drag | drag, whileDrag | Draggable elements |
| Focus | whileFocus | Keyboard navigation |

## Basic Hover and Tap

```tsx
import { motion } from 'motion/react'

export function Button({ children, onClick }) {
  return (
    <motion.button
      whileHover={{ scale: 1.05, y: -2 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className="btn"
    >
      {children}
    </motion.button>
  )
}
```

**Good Practices**:
- Keep hover/tap animations fast (100-200ms)
- Scale 1.05 for slight growth on hover
- Scale 0.95 for press feedback
- Use y offset for lift effect

## Drag Basics

```tsx
export function DraggableBox() {
  return (
    <motion.div
      drag
      className="box"
    />
  )
}
```

This allows dragging in any direction. Usually you want constraints:

```tsx
export function ConstrainedDrag() {
  return (
    <motion.div
      drag
      dragConstraints={{ left: -100, right: 100, top: -100, bottom: 100 }}
      className="box"
    />
  )
}
```

## Drag with Constraints

### Fixed Constraints

```tsx
<motion.div
  drag
  dragConstraints={{ left: -50, right: 50, top: 0, bottom: 100 }}
>
  Draggable
</motion.div>
```

### Parent Constraints (Better for responsive)

```tsx
const ref = useRef(null)

return (
  <div ref={ref} className="container">
    <motion.div
      drag
      dragConstraints={ref}  // Constrain to parent
    >
      Draggable
    </motion.div>
  </div>
)
```

## Drag with Elasticity

Add spring-like feel to dragging:

```tsx
export function ElasticDrag() {
  return (
    <motion.div
      drag
      dragElastic={0.3}  // 0 = no elasticity, 1 = full elasticity
      className="box"
    />
  )
}
```

- `dragElastic={0}` - Hard boundary, no bounce
- `dragElastic={0.2}` - Slight bounce
- `dragElastic={0.5}` - More spring-like

## Dragging with Friction

Slow down drag with friction:

```tsx
<motion.div
  drag
  dragElastic={0.2}
  dragTransition={{ power: 0.3, restDelta: 10 }}
>
  Draggable with friction
</motion.div>
```

Drag continues sliding after mouse release, gradually stopping.

## Swipe to Dismiss Pattern

```tsx
export function SwipeablCard({ item, onDismiss }) {
  const ref = useRef(null)

  return (
    <motion.div
      ref={ref}
      drag="x"  // Only drag horizontally
      dragConstraints={{ left: -200, right: 200 }}
      dragElastic={0.3}
      onDragEnd={(event, info) => {
        if (Math.abs(info.offset.x) > 100) {
          onDismiss(item.id)
        }
      }}
      className="card"
    >
      {item.content}
    </motion.div>
  )
}
```

**Key Points**:
- `drag="x"` limits to horizontal dragging
- Check `info.offset.x` to detect swipe distance
- Dismiss if swipe distance > threshold
- onDragEnd fires after drag completes

## Scroll Driven Animations

Create animations based on scroll position:

```tsx
import { useScroll, useTransform, motion } from 'motion/react'

export function ScrollProgress() {
  const { scrollY } = useScroll()
  const scaleX = useTransform(scrollY, [0, 1000], [0, 1])

  return (
    <motion.div
      style={{ scaleX, transformOrigin: '0%' }}
      className="progress-bar"
    />
  )
}
```

## Focus State for Keyboard Navigation

```tsx
export function AccessibleButton({ children }) {
  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileFocus={{ scale: 1.05, outline: '2px solid blue' }}
      onFocus={() => console.log('focused')}
    >
      {children}
    </motion.button>
  )
}
```

## Combined Gestures

```tsx
export function InteractiveCard({ item }) {
  return (
    <motion.div
      drag
      dragConstraints={{ left: -50, right: 50, top: -50, bottom: 50 }}
      dragElastic={0.2}
      whileHover={{ scale: 1.02, boxShadow: '0 10px 20px rgba(0,0,0,0.1)' }}
      whileTap={{ scale: 0.98 }}
      whileDrag={{ opacity: 0.7 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className="card"
    >
      {item.content}
    </motion.div>
  )
}
```

## Gesture State Callbacks

Handle drag events:

```tsx
export function DragExample() {
  return (
    <motion.div
      drag
      onDragStart={(event, info) => {
        console.log('Drag started')
      }}
      onDrag={(event, info) => {
        console.log('Dragging:', info.point)
      }}
      onDragEnd={(event, info) => {
        console.log('Drag ended:', info.velocity)
      }}
    >
      Draggable
    </motion.div>
  )
}
```

Available event info:
- `info.point` - Current pointer position
- `info.delta` - Movement since last event
- `info.offset` - Total movement from start
- `info.velocity` - Current velocity vector

## Performance Tips

1. **Memoize gesture components** to prevent re-renders
2. **Use willChange** for GPU hints:
   ```tsx
   <motion.div drag style={{ willChange: 'transform' }}>
   ```
3. **Debounce callbacks** if they're expensive
4. **Use refs for constraints** instead of fixed values
5. **Test on real devices** - touch feels different from mouse

## Accessibility

Always ensure gesture elements are accessible:

```tsx
<motion.button
  drag
  dragConstraints={{ left: -50, right: 50 }}
  whileHover={{ scale: 1.05 }}
  whileFocus={{ scale: 1.05, outline: '2px solid blue' }}
  aria-label="Draggable button"
  role="button"
  tabIndex={0}
>
  Drag me
</motion.button>
```

## Common Mistakes

### ❌ No dragConstraints

```tsx
// Bad - can drag anywhere
<motion.div drag>{content}</motion.div>

// Good - constrained drag
<motion.div
  drag
  dragConstraints={{ left: -100, right: 100 }}
>
  {content}
</motion.div>
```

### ❌ Missing event handlers

```tsx
// Bad - nothing happens after drag
<motion.div drag>Draggable</motion.div>

// Good - handle drag completion
<motion.div
  drag
  onDragEnd={(e, info) => handleDragEnd(info)}
>
  Draggable
</motion.div>
```

### ❌ Gesture animations too slow

```tsx
// Bad - feels sluggish
<motion.button
  whileHover={{ scale: 1.1 }}
  transition={{ duration: 0.5 }}
>

// Good - feels responsive
<motion.button
  whileHover={{ scale: 1.05 }}
  transition={{ duration: 0.15 }}
>
```

## Best Practices

1. **Keep gesture animations fast** (100-200ms)
2. **Use appropriate scale values** (1.05 for hover, 0.95 for tap)
3. **Always set dragConstraints** to prevent unexpected behavior
4. **Provide visual feedback** for all gestures
5. **Test accessibility** - keyboard and touch
6. **Use spring transitions** for gesture feedback
7. **Memoize gesture components** to prevent re-renders
