# global overlay for Motion pack

<!-- EXTEND: TechStack -->
## Motion Animation Validation Context

### Guidelines
- AnimatePresence patterns for mount/unmount animations with exit states
- Layout animations using layout prop and layoutId for reflows
- Gesture handling with drag, hover, tap animations
- Variants system for reusable animation definitions
- Performance optimization: GPU-accelerated transforms only (x, y, rotate, opacity, scale)

### Concrete Checks
- All AnimatePresence components have exit animations defined
- Layout changes use layout prop, not manual positioning
- Drag constraints and elastic values configured appropriately
- Variants defined for complex or repeated animations
- Only transform and opacity properties animated (no width/height/etc)
- Memoized components in animated lists to prevent re-renders
- willChange hints for complex animations
<!-- /EXTEND -->
