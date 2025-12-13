# Variants System

## Overview

Variants are animation objects that define multiple states. Instead of writing animation properties inline, you define them once and reuse them throughout your component. This makes animations more maintainable, testable, and easier to iterate on.

## Why Variants Matter

### ❌ Without Variants (Repetitive, Hard to Change)

```tsx
export function Card({ hover }) {
  return (
    <motion.div
      animate={hover ? {
        scale: 1.05,
        boxShadow: '0 10px 20px rgba(0,0,0,0.1)',
        y: -5
      } : {
        scale: 1,
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
        y: 0
      }}
      transition={{ duration: 0.3 }}
    >
      Content
    </motion.div>
  )
}
```

### ✅ With Variants (Clean, Reusable)

```tsx
const cardVariants = {
  rest: {
    scale: 1,
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
    y: 0
  },
  hover: {
    scale: 1.05,
    boxShadow: '0 10px 20px rgba(0,0,0,0.1)',
    y: -5
  }
}

export function Card() {
  return (
    <motion.div
      variants={cardVariants}
      initial="rest"
      whileHover="hover"
      transition={{ duration: 0.3 }}
    >
      Content
    </motion.div>
  )
}
```

## Basic Variants

```tsx
const buttonVariants = {
  rest: {
    scale: 1,
    opacity: 1
  },
  hover: {
    scale: 1.05,
    opacity: 0.8
  },
  pressed: {
    scale: 0.95,
    opacity: 0.6
  }
}

export function Button({ children }) {
  return (
    <motion.button
      variants={buttonVariants}
      initial="rest"
      whileHover="hover"
      whileTap="pressed"
    >
      {children}
    </motion.button>
  )
}
```

## Variant Inheritance (Critical)

Variants propagate from parent to children automatically:

```tsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,  // Delay each child by 0.1s
      delayChildren: 0.3,    // Start children after 0.3s
    }
  }
}

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: { y: 0, opacity: 1 }
}

export function List({ items }) {
  return (
    <motion.ul
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {items.map(item => (
        <motion.li
          key={item.id}
          variants={itemVariants}
          // Automatically uses "hidden" and "visible" from container
        >
          {item.name}
        </motion.li>
      ))}
    </motion.ul>
  )
}
```

**Key Insight**: Children inherit variant names but use their own variant definitions. This creates orchestrated animations with minimal code.

## Stagger Children

Stagger children animations for visual flow:

```tsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,  // Each child starts 0.1s after previous
    }
  }
}

const itemVariants = {
  hidden: { x: -20, opacity: 0 },
  visible: { x: 0, opacity: 1 }
}
```

Results in:
- Child 0: starts at 0ms
- Child 1: starts at 100ms
- Child 2: starts at 200ms
- etc.

## Delay Children

Start all children after a delay:

```tsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      delayChildren: 0.5,    // Start all children at 0.5s
      staggerChildren: 0.1,  // Then stagger them
    }
  }
}
```

Timeline:
- Container parent animates: 0ms → 0.5s
- All children start: 0.5s
- First child: 0.5s
- Second child: 0.6s
- Third child: 0.7s
- etc.

## Custom Properties in Variants

Pass dynamic values through custom properties:

```tsx
const itemVariants = {
  hidden: { opacity: 0, x: (index) => -20 * (index + 1) },
  visible: { opacity: 1, x: 0 }
}

export function List({ items }) {
  return (
    <motion.ul>
      {items.map((item, index) => (
        <motion.li
          key={item.id}
          variants={itemVariants}
          custom={index}  // Pass index to variants
          initial="hidden"
          animate="visible"
        >
          {item.name}
        </motion.li>
      ))}
    </motion.ul>
  )
}
```

## Complex Animation States

Define multiple states with different transitions:

```tsx
const formVariants = {
  hidden: {
    opacity: 0,
    y: -20
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: 'easeOut'
    }
  },
  error: {
    x: [0, -10, 10, -10, 0],  // Shake animation
    transition: {
      duration: 0.4,
      ease: 'easeInOut'
    }
  },
  loading: {
    opacity: [1, 0.5, 1],
    transition: {
      repeat: Infinity,
      duration: 1
    }
  }
}

export function Form({ status, onSubmit }) {
  return (
    <motion.form
      variants={formVariants}
      initial="hidden"
      animate={status === 'error' ? 'error' : status === 'loading' ? 'loading' : 'visible'}
    >
      {fields}
    </motion.form>
  )
}
```

## Variant Transitions

Define transitions per variant for consistency:

```tsx
const cardVariants = {
  rest: {
    scale: 1,
    transition: { duration: 0.2 }
  },
  hover: {
    scale: 1.1,
    transition: { duration: 0.3 }
  },
  exit: {
    scale: 0,
    opacity: 0,
    transition: { duration: 0.2 }
  }
}

<motion.div variants={cardVariants} initial="rest" whileHover="hover" />
```

## Orchestrating Complex Animations

```tsx
const pageVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.3,
    }
  }
}

const headerVariants = {
  hidden: { y: -20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: { duration: 0.5 }
  }
}

const contentVariants = {
  hidden: { x: -20, opacity: 0 },
  visible: {
    x: 0,
    opacity: 1,
    transition: { duration: 0.4 }
  }
}

export function Page() {
  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.header variants={headerVariants}>Header</motion.header>
      <motion.main variants={contentVariants}>Content</motion.main>
      <motion.footer variants={contentVariants}>Footer</motion.footer>
    </motion.div>
  )
}
```

Timeline:
- Page container animates opacity: 0s → visible
- Header animates: 0.3s → 0.8s
- Main content: 0.4s → 0.8s
- Footer: 0.5s → 0.9s

## Exporting and Reusing Variants

Create variant libraries for consistency:

```tsx
// animations/cardVariants.ts
export const cardVariants = {
  rest: {
    scale: 1,
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
  },
  hover: {
    scale: 1.05,
    boxShadow: '0 10px 20px rgba(0,0,0,0.1)'
  }
}

// animations/listVariants.ts
export const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

export const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 }
}

// In component
import { cardVariants } from '<variants-module>'
import { containerVariants, itemVariants } from '<variants-module>'

export function Gallery({ cards }) {
  return (
    <motion.div variants={containerVariants} initial="hidden" animate="visible">
      {cards.map(card => (
        <motion.div key={card.id} variants={itemVariants} variants={cardVariants}>
          {card.content}
        </motion.div>
      ))}
    </motion.div>
  )
}
```

## Best Practices

1. **Extract variants to const objects** - easier to maintain and test
2. **Reuse variant names** - hidden/visible for consistency
3. **Use staggerChildren** for lists to feel orchestrated
4. **Set transitions per variant** when timing differs
5. **Combine variants** with AnimatePresence for complete flows
6. **Document complex variants** - explain the animation sequence
7. **Use custom** prop for dynamic behavior
8. **Create variant libraries** for design system consistency

## Common Mistakes

### ❌ Variants without transitions

```tsx
// Bad - uses default transition
const variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 }
}

// Good - explicit transition
const variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.3 }
  }
}
```

### ❌ Forgetting variant inheritance

```tsx
// Bad - parent and child use different states
<motion.div initial="hidden" animate="visible">
  <motion.div initial="off" animate="on">
    {/* Won't inherit parent variants! */}
  </motion.div>
</motion.div>

// Good - child uses same variant names
<motion.div
  variants={containerVariants}
  initial="hidden"
  animate="visible"
>
  <motion.div variants={itemVariants}>
    {/* Automatically uses hidden/visible */}
  </motion.div>
</motion.div>
```

### ❌ Over-complicating variants

```tsx
// Bad - too complex in one variant
const variants = {
  visible: {
    opacity: 1,
    x: 0,
    y: 0,
    rotate: 0,
    scale: 1,
    // ... 20 more properties
  }
}

// Good - focused, clear purpose
const variants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 }
}
```
