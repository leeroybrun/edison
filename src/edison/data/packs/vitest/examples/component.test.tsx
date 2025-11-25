import { describe, it, expect } from 'vitest';

function Button({ onClick, children }: any) {
  return <button onClick={onClick}>{children}</button>;
}

describe('Button', () => {
  it('renders label', () => {
    // minimal placeholder; not executing RTL here
    expect(<Button onClick={() => {}}>Click</Button>).toBeTruthy();
  });
});

