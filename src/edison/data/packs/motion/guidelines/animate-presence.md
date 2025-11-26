# AnimatePresence Patterns

## Overview

AnimatePresence is the Motion component that handles animations when elements mount and unmount. Without AnimatePresence, exiting animations won't play because React removes the component from the DOM immediately.

## The Problem It Solves

When you remove a component from the DOM, React immediately unmounts it. If you want an exit animation, the component needs to stay in the DOM during the animation. AnimatePresence delays the unmount until the exit animation completes.

```tsx
// Without AnimatePresence - no exit animation!
{isOpen && <motion.div animate={{ opacity: 1 }} exit={{ opacity: 0 }} />}

// With AnimatePresence - exit animation plays
<AnimatePresence>
  {isOpen && <motion.div animate={{ opacity: 1 }} exit={{ opacity: 0 }} />}
</AnimatePresence>
```

## Basic Pattern

```tsx
import { AnimatePresence, motion } from 'motion/react'

export function Modal({ isOpen, onClose }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="modal-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="modal-content"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {content}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
```

## Modes

AnimatePresence has three modes to handle timing:

### 1. mode="wait" - Sequential Animation

Wait for exit to complete before entering next element. Good for page transitions.

```tsx
<AnimatePresence mode="wait">
  {currentTab === 'a' && <TabA />}
  {currentTab === 'b' && <TabB />}
</AnimatePresence>
```

- TabA exits completely
- Then TabB enters

### 2. mode="sync" - Simultaneous Animation (Default)

Exit and enter happen at same time. Good for overlays.

```tsx
<AnimatePresence mode="sync">
  {notifications.map(notification => (
    <Notification key={notification.id} notification={notification} />
  ))}
</AnimatePresence>
```

- Notification exits while new one enters
- Faster but can feel busy

### 3. mode="popLayout" - Remove from Layout Immediately

Remove from layout immediately but animate exit. Best for lists. **Most performant.**

```tsx
<AnimatePresence mode="popLayout">
  {items.map(item => (
    <motion.div key={item.id} exit={{ opacity: 0 }}>
      {item.content}
    </motion.div>
  ))}
</AnimatePresence>
```

- Item removed from layout immediately
- But opacity animation still plays
- Great for lists where order matters

## Common Patterns

### Notification Stack

```tsx
export function NotificationStack({ notifications }) {
  return (
    <div className="notification-stack">
      <AnimatePresence mode="popLayout">
        {notifications.map((notification, index) => (
          <motion.div
            key={notification.id}
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
            transition={{ duration: 0.2 }}
            style={{ position: 'absolute', top: index * 80 }}
          >
            {notification.message}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
```

### Accordion with AnimatePresence

```tsx
export function AccordionItem({ title, content, isOpen, onClick }) {
  return (
    <div>
      <button onClick={onClick}>{title}</button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="content"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            {content}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
```

### Conditional Rendering with Transitions

```tsx
export function Tabs({ activeTab, tabs }) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.3 }}
      >
        {tabs[activeTab]?.content}
      </motion.div>
    </AnimatePresence>
  )
}
```

## Important Props

| Prop | Purpose | Default |
|------|---------|---------|
| mode | Animation timing: wait, sync, popLayout | "sync" |
| initial | Whether to animate on mount | true |
| onExitComplete | Callback when all exits complete | - |
| custom | Pass dynamic data to variants | - |

## Best Practices

1. **Always use AnimatePresence** when removing elements
2. **Set mode explicitly** - don't rely on defaults
3. **Define exit animations** - every element should have an exit
4. **Use unique keys** - required for tracking elements
5. **Keep animations fast** - 200-400ms for exit/enter
6. **Test with real data** - animations work differently with variable content
