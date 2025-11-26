# Performance Optimization for Animations

## Overview

Animations can be beautiful, but poor performance makes them feel terrible. Maintaining 60fps (16.7ms per frame) is critical for smooth user experience.

## The Golden Rule: GPU-Accelerated Properties Only

Only animate properties that don't trigger layout recalculations (reflow/repaint). GPU-accelerated properties are fast; others are slow.

### ✅ FAST - GPU Accelerated

These properties skip layout recalculation:

- **transform**: `translate`, `rotate`, `scale`, `skew`
- **opacity**: transparency changes
- **filter**: blur, brightness, etc. (use sparingly)

```tsx
// ✅ GOOD - All GPU-accelerated
<motion.div
  animate={{
    x: 100,        // transform: translateX
    y: 50,         // transform: translateY
    rotate: 45,    // transform: rotate
    scale: 1.2,    // transform: scale
    opacity: 0.8   // opacity
  }}
>
  Smooth animation
</motion.div>
```

### ❌ SLOW - Layout Recalculation

These properties trigger expensive reflow/repaint:

- **width**, **height**: resize
- **top**, **left**, **right**, **bottom**: positioning
- **margin**, **padding**: spacing
- **border**: outline changes
- **background-color**: color changes
- **font-size**: text changes

```tsx
// ❌ BAD - Triggers reflow on every frame
<motion.div
  animate={{
    width: 200,      // ❌ reflow
    height: 200,     // ❌ reflow
    left: 100,       // ❌ reflow
    paddingLeft: 20, // ❌ reflow
  }}
>
  Jerky animation
</motion.div>
```

## Transform Instead of Position

### ❌ Bad: Animating position properties

```tsx
<motion.div
  animate={{ left: 100, top: 50 }}
>
  Content
</motion.div>
```

Every frame: measure → calculate layout → paint ❌

### ✅ Good: Using transforms

```tsx
<motion.div
  animate={{ x: 100, y: 50 }}
>
  Content
</motion.div>
```

Every frame: apply transform only ✅

**Performance impact**: 3-5x faster with transforms!

## Memoization for List Animations

Prevent unnecessary re-renders when animating list items:

```tsx
import { memo } from 'react'
import { motion } from 'motion/react'

// ❌ BAD - Re-renders entire list on parent state change
export function ItemList({ items, selectedId }) {
  return (
    <div>
      {items.map(item => (
        <motion.div
          key={item.id}
          animate={{
            scale: selectedId === item.id ? 1.1 : 1,
            opacity: selectedId === item.id ? 1 : 0.5
          }}
        >
          {item.name}
        </motion.div>
      ))}
    </div>
  )
}

// ✅ GOOD - Only animated items re-render
const AnimatedItem = memo(function AnimatedItem({ item, isSelected }) {
  return (
    <motion.div
      animate={{
        scale: isSelected ? 1.1 : 1,
        opacity: isSelected ? 1 : 0.5
      }}
    >
      {item.name}
    </motion.div>
  )
})

export function ItemList({ items, selectedId }) {
  return (
    <div>
      {items.map(item => (
        <AnimatedItem
          key={item.id}
          item={item}
          isSelected={selectedId === item.id}
        />
      ))}
    </div>
  )
}
```

**Performance**: memo() prevents 100+ re-renders on selection change.

## willChange CSS Hint

Tell browser to optimize specific properties:

```tsx
// ✅ Good - GPU hint for complex animation
<motion.div
  animate={{ rotate: 360 }}
  transition={{ duration: 2, repeat: Infinity }}
  style={{ willChange: 'transform' }}
>
  {spinner}
</motion.div>
```

`willChange` prepares GPU for animations. Use sparingly (max 3 properties).

## Reduce Animation Complexity

### ❌ Bad: Animating many properties

```tsx
<motion.div
  animate={{
    x: 100,
    y: 50,
    rotate: 45,
    scale: 1.2,
    opacity: 0.8,
    borderRadius: 20,        // ❌ expensive
    boxShadow: '...',        // ❌ very expensive
    filter: 'blur(10px)',    // ❌ very expensive
    backgroundColor: '#000'  // ❌ triggers repaint
  }}
  transition={{ duration: 2 }}
>
  Too much
</motion.div>
```

### ✅ Good: Focused animations

```tsx
<motion.div
  animate={{
    x: 100,
    y: 50,
    rotate: 45,
    scale: 1.2,
    opacity: 0.8
  }}
  transition={{ duration: 0.3 }}
>
  Smooth
</motion.div>
```

## Layout Animations Performance

Use `layout` prop efficiently:

```tsx
// ✅ GOOD - Layout on container
<motion.div layout>
  {items.map(item => <Item key={item.id} />)}
</motion.div>

// ❌ BAD - Layout on every item (unnecessary)
<motion.div>
  {items.map(item => (
    <motion.div key={item.id} layout>
      <Item />
    </motion.div>
  ))}
</motion.div>
```

Use `layoutDependency` to prevent recalculations:

```tsx
<motion.div
  layout
  layoutDependency={filterText}  // Only recalculate on filter change
>
  {filtered.map(item => <Item key={item.id} />)}
</motion.div>
```

## Transition Timing

### ❌ Bad: Animations too long

```tsx
<motion.div
  animate={{ opacity: 1 }}
  transition={{ duration: 2 }}  // ❌ Feels slow
>
  Content
</motion.div>
```

### ✅ Good: Appropriate timing

```tsx
// UI feedback: 100-150ms
<motion.button whileTap={{ scale: 0.95 }} transition={{ duration: 0.1 }} />

// Entrance animation: 200-400ms
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.3 }}
/>

// Exit animation: 200-300ms
<motion.div
  exit={{ opacity: 0 }}
  transition={{ duration: 0.2 }}
/>
```

Keep animations snappy for UI responsiveness.

## Avoiding Layout Shift

Layout shift (moving content during animation) creates jank:

```tsx
// ❌ BAD - Causes layout shift
<AnimatePresence>
  {notification && (
    <motion.div
      key="notification"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
    >
      {notification.message}
    </motion.div>
  )}
</AnimatePresence>
{/* Content below shifts up/down */}

// ✅ GOOD - Fixed space prevents shift
<div style={{ height: notification ? 'auto' : 0, overflow: 'hidden' }}>
  <AnimatePresence>
    {notification && (
      <motion.div
        key="notification"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        {notification.message}
      </motion.div>
    )}
  </AnimatePresence>
</div>
```

## Measuring Performance

Use DevTools to verify 60fps:

1. **Chrome DevTools Performance tab**:
   - Record animation
   - Check FPS graph (should be consistently 60fps)
   - Look for red zones = dropped frames

2. **React DevTools Profiler**:
   - Check component render times
   - Identify unnecessary re-renders
   - Verify memoization working

3. **Lighthouse/Web Vitals**:
   - Monitor Interaction to Next Paint (INP)
   - Should be < 200ms

## Vendor Prefixes

Some older browsers need prefixes:

```tsx
<motion.div
  animate={{ rotate: 360 }}
  style={{
    willChange: 'transform',
    WebkitTransform: 'rotate(360deg)',  // Safari
  }}
/>
```

Motion handles most prefixes automatically.

## Animation Limits

For smoothness, follow these limits:

| Scenario | Limit | Reason |
|----------|-------|--------|
| Simultaneous animations | < 20 | Browser can't handle more |
| Staggered items | < 100 | Re-render performance |
| Animation duration | 100-500ms | Feels responsive |
| Gesture feedback | 100-200ms | Immediate feedback |

## Best Practices Checklist

- ✅ Animate only transform and opacity
- ✅ Use memo() for list items
- ✅ Add willChange for complex animations
- ✅ Set explicit transitions (no defaults)
- ✅ Keep animations < 500ms
- ✅ Use layoutDependency for layout animations
- ✅ Test on real devices
- �� Monitor performance with DevTools
- ❌ Don't animate width/height
- ❌ Don't animate multiple colors
- ❌ Don't animate without memoization
- ❌ Don't use blur/shadow filters

## Common Performance Issues

### Issue: Dropped frames during drag

**Cause**: Re-renders during drag
**Solution**: Memoize draggable components, use useMotionValue

### Issue: Staggered animations feel sluggish

**Cause**: Too many simultaneous re-renders
**Solution**: Use layoutDependency, increase stagger timing

### Issue: Layout shift when adding/removing items

**Cause**: Content reflows during animation
**Solution**: Fix container height during animation with overflow: hidden

### Issue: Animations stutter on mobile

**Cause**: Insufficient GPU power
**Solution**: Reduce animation complexity, decrease simultaneous animations
