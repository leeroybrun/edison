# Component Testing

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
### Component testing (Vitest + Testing Library)

- Interact like users: drive events and assert DOM updates.
- Prefer queries by role/label/text; avoid test IDs unless necessary.
- Keep tests isolated; render fresh components per test.

#### Minimal illustrative pattern

```typescript
import { it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

it('submits form', async () => {
  const user = userEvent.setup()
  render(<MyForm />)

  await user.type(screen.getByLabelText(/email/i), 'a@b.com')
  await user.click(screen.getByRole('button', { name: /submit/i }))

  expect(await screen.findByText(/success/i)).toBeInTheDocument()
})
```
<!-- /section: patterns -->

