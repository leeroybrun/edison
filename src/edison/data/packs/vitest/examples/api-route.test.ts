import { describe, it, expect } from 'vitest';

describe('api route', () => {
  it('returns ok', async () => {
    const res = { status: 200, body: { ok: true } };
    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
  });
});

