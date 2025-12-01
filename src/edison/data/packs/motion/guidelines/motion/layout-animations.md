# Layout Animations

## Overview

Layout animations automatically animate position and size changes without manual measurement. When you add the `layout` prop to a motion component, Motion tracks its position and size, and smoothly animates to the new position/size when it changes.

## The Problem It Solves

Without layout animations, DOM reflows cause instant, jarring layout changes. Layout animations make these changes smooth and feel intentional.

```tsx
// Without layout - instant jump
{expanded && <div>{content}</div>}

// With layout - smooth animation
{expanded && <motion.div layout>{content}</motion.div>}
```

## Basic Pattern

```tsx
import { motion } from 'motion/react'

export function ExpandableSection({ title, content }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <motion.div layout className="section">
      <button onClick={() => setExpanded(!expanded)}>{title}</button>
      {expanded && (
        <motion.div layout className="content">
          {content}
        </motion.div>
      )}
    </motion.div>
  )
}
```

## How It Works

1. Motion measures the element's position and size
2. When layout changes, new position/size is calculated
3. Motion animates from old to new state
4. All done without manual measurements!

## Layout ID for Shared Elements

Use `layoutId` for animated transitions between different elements:

```tsx
export function ImageGallery({ selectedId, images }) {
  const selected = images.find(img => img.id === selectedId)

  return (
    <div className="gallery">
      {/* Small image grid */}
      <div className="grid">
        {images.map(img => (
          <motion.img
            key={img.id}
            src={img.thumb}
            layoutId={`image-${img.id}`}
            onClick={() => setSelectedId(img.id)}
            className={selectedId === img.id ? 'active' : ''}
          />
        ))}
      </div>

      {/* Large image view */}
      {selected && (
        <motion.div layoutId={`image-${selected.id}`} className="large">
          <motion.img src={selected.full} />
        </motion.div>
      )}
    </div>
  )
}
```

This creates a "shared layout animation" where the image appears to move and resize from the grid to the large view.

## Grid Reflow

Perfect for responsive grids that reflow:

```tsx
export function ResponsiveGrid({ items, columns }) {
  return (
    <motion.div
      layout
      className="grid"
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gap: 16
      }}
    >
      {items.map(item => (
        <motion.div
          key={item.id}
          layout  // Each item also animates
          className="card"
        >
          {item.content}
        </motion.div>
      ))}
    </motion.div>
  )
}
```

When columns change, all cards smoothly animate to new positions.

## List Reordering

Animate list items when order changes:

```tsx
export function SortableList({ items, order }) {
  const sorted = order === 'asc'
    ? items.sort((a, b) => a.name.localeCompare(b.name))
    : items

  return (
    <motion.ul layout>
      {sorted.map(item => (
        <motion.li
          key={item.id}
          layout  // Animate position change
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          {item.name}
        </motion.li>
      ))}
    </motion.ul>
  )
}
```

## Accordion with Layout

```tsx
export function Accordion({ items }) {
  const [expanded, setExpanded] = useState(null)

  return (
    <motion.div layout className="accordion">
      {items.map(item => (
        <motion.div key={item.id} layout className="item">
          <button onClick={() => setExpanded(expanded === item.id ? null : item.id)}>
            {item.title}
          </button>
          {expanded === item.id && (
            <motion.div layout className="content">
              {item.content}
            </motion.div>
          )}
        </motion.div>
      ))}
    </motion.div>
  )
}
```

## Performance Considerations

Layout animations are efficient because Motion uses transforms, not repositioning. However:

1. **Don't overuse on large lists** - 100+ items may cause performance issues
2. **Use layoutDependency** to trigger animations on specific changes
3. **Consider virtualization** for very long lists
4. **Pair with memo()** to prevent unnecessary recalculations

```tsx
const ListItem = memo(function ListItem({ item }) {
  return (
    <motion.div layout>
      {item.content}
    </motion.div>
  )
})
```

## Layout Dependencies

Control when layout animations trigger:

```tsx
export function DynamicList({ items, filterText }) {
  return (
    <motion.div
      layout
      layoutDependency={filterText}  // Only animate when filter changes
    >
      {items
        .filter(item => item.name.includes(filterText))
        .map(item => (
          <motion.div key={item.id} layout>
            {item.name}
          </motion.div>
        ))}
    </motion.div>
  )
}
```

Without layoutDependency, Motion recalculates on every render (expensive).

## Common Mistakes

### ❌ Animating width/height instead of layout

```tsx
// Bad - triggers reflow
<motion.div
  animate={{ width: expanded ? 300 : 100 }}
>
  {content}
</motion.div>

// Good - smooth layout animation
<motion.div layout>
  {expanded && <div className="extra-content" />}
</motion.div>
```

### ❌ Missing layoutId in shared animations

```tsx
// Bad - two separate animations
<motion.div>Photo</motion.div>
<motion.div>Photo</motion.div>

// Good - connected animation with layoutId
<motion.div layoutId="photo">Photo</motion.div>
<motion.div layoutId="photo">Photo</motion.div>
```

### ❌ Layout on every element

```tsx
// Bad - unnecessary calculations
<motion.div layout>
  <motion.div layout>
    <motion.div layout>
      Content
    </motion.div>
  </motion.div>
</motion.div>

// Good - layout on container only
<motion.div layout>
  <div>
    <div>
      Content
    </div>
  </div>
</motion.div>
```

## Best Practices

1. **Use layout for structure changes** - adding/removing content, reordering
2. **Pair with transforms** - combine layout with x, y for complex animations
3. **Set explicit transitions** - `transition={{ type: 'spring' }}` for natural feel
4. **Use layoutDependency** - prevent unnecessary recalculations
5. **Test performance** - layout animations at scale may need optimization
6. **Measure in DevTools** - ensure 60fps smooth animations
