import { createTwoFilesPatch } from 'diff';
import { describe, expect, it } from 'vitest';

import { applyUnifiedDiff } from '../src/services/diff-utils';

describe('applyUnifiedDiff', () => {
  it('applies a valid diff', () => {
    const original = 'Hello world\nLine two';
    const target = 'Hello Edison\nLine two';
    const diff = createTwoFilesPatch('a', 'b', original, target);
    const result = applyUnifiedDiff(original, diff);
    expect(result).toBe(target);
  });

  it('throws on empty diff payload', () => {
    expect(() => applyUnifiedDiff('foo', '')).toThrowError(/empty/);
  });

  it('throws when diff changes too much content', () => {
    const original = 'short';
    const target = 'This is a very long replacement line that exceeds the ratio';
    const diff = createTwoFilesPatch('a', 'b', original, target);
    expect(() => applyUnifiedDiff(original, diff, 0.2)).toThrowError(/too much/);
  });
});
