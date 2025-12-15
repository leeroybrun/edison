# TDD Workflow

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
### TDD workflow (Vitest)

- Follow core TDD (see constitution): tests-first, minimal green, then refactor.
- Keep the loop tight: run the smallest scope that proves correctness, then expand.

#### Micro-template

```typescript
import { describe, it, expect } from 'vitest'

describe('feature', () => {
  it('RED: fails before implementation exists', () => {
    // Arrange
    // Act
    // Assert
    expect(actual).toEqual(expected)
  })
})
```
<!-- /section: patterns -->
