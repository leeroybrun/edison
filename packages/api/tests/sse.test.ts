import { describe, expect, it } from 'vitest';

import { serializeSSEEvent } from '../src/sse/iteration-stream';

describe('serializeSSEEvent', () => {
  it('formats data as an SSE payload', () => {
    const payload = serializeSSEEvent('status', { status: 'EXECUTING' });
    expect(payload).toBe('event: status\ndata: {"status":"EXECUTING"}\n\n');
  });
});
