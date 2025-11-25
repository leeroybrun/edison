'use client';
import { useState } from 'react';

export default function ClientComponent() {
  const [count, setCount] = useState(0);
  return (
    <button aria-label="increment" onClick={() => setCount((c) => c + 1)}>
      Count: {count}
    </button>
  );
}

