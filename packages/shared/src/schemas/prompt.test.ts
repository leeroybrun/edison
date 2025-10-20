import { describe, expect, it } from 'vitest';
import { PromptSchema } from './prompt';

describe('PromptSchema', () => {
  it('validates prompts with few-shots correctly', () => {
    const parsed = PromptSchema.parse({
      name: 'Support agent',
      systemText: 'You are a helpful assistant.',
      text: 'Answer the customer question.',
      fewShots: [
        { user: 'Hello?', assistant: 'Hi! How can I assist you today?' },
      ],
    });

    expect(parsed.fewShots?.length).toBe(1);
  });

  it('rejects prompts with empty text', () => {
    expect(() =>
      PromptSchema.parse({
        name: 'Broken prompt',
        text: '',
      }),
    ).toThrowError(/text/);
  });
});
