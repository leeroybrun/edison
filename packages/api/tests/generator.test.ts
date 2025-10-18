import { describe, expect, it } from 'vitest';
import { parseSyntheticCasePayload } from '../src/services/generator';

describe('parseSyntheticCasePayload', () => {
  it('parses valid cases and enforces uniqueness', () => {
    const raw = JSON.stringify([
      { input: { question: 'Hi' }, tags: ['a', 'a'], difficulty: 4 },
      { input: { question: 'Hi' }, tags: ['duplicate'] },
      { input: { question: 'Bye' }, tags: ['b'] },
    ]);

    const { cases, discarded } = parseSyntheticCasePayload(raw, 10);
    expect(cases).toHaveLength(2);
    expect(discarded).toBe(1);
    expect(cases[0].tags).toEqual(['a']);
  });

  it('throws when JSON is invalid', () => {
    expect(() => parseSyntheticCasePayload('{', 5)).toThrowError(/valid JSON/);
  });

  it('throws when no valid cases returned', () => {
    const raw = JSON.stringify([{ foo: 'bar' }]);
    expect(() => parseSyntheticCasePayload(raw, 3)).toThrowError(/valid test cases/);
  });
});
