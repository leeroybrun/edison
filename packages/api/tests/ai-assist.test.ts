import { describe, expect, it } from 'vitest';

import type { LLMAdapter } from '../src/llm/types';
import { AIAssistService } from '../src/services/ai-assist';

class FakeFactory {
  async tryGetAdapterForProject(): Promise<LLMAdapter | null> {
    return null;
  }

  async tryGetGlobalAdapter(): Promise<LLMAdapter | null> {
    return null;
  }
}

describe('AIAssistService', () => {
  const service = new AIAssistService(new FakeFactory() as unknown as any);

  it('provides deterministic objective fallbacks', async () => {
    const result = await service.draftObjectives('Improve customer responses', 2);
    expect(result.options).toHaveLength(2);
    expect(result.options[0].title).toBe('Objective 1');
  });

  it('provides deterministic rubric fallback', async () => {
    const result = await service.draftRubric('Answer billing questions accurately');
    const weights = result.criteria.map((item) => item.weight);
    expect(weights.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 5);
  });

  it('provides deterministic prompt fallback', async () => {
    const rubric = [
      { name: 'Accuracy', description: 'Be right', weight: 0.5, scale: { min: 1, max: 5 } },
      { name: 'Tone', description: 'Friendly', weight: 0.5, scale: { min: 1, max: 5 } },
    ];
    const result = await service.draftPrompts('Help customers', rubric, 1);
    expect(result.prompts).toHaveLength(1);
    expect(result.prompts[0].text).toContain('Help customers');
  });

  it('improves prompt with fallback guidance', async () => {
    const result = await service.improvePrompt({ text: 'Respond politely.' }, 'Assist users', undefined);
    expect(result.improved).toContain('Clarifications');
    expect(result.changes).toContain('Appended');
  });
});
