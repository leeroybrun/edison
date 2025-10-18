import type { PromptConfig, Rubric } from '@edison/shared';

import type { LLMAdapter } from '../llm/types';

import { applyUnifiedDiff } from './diff-utils';

export interface RefinementInput {
  goal: string;
  rubric: Rubric;
  prompt: PromptConfig;
  adapter: LLMAdapter;
  diagnostics: string;
}

export interface RefinementResult {
  diff: string;
  note: string;
  updatedPrompt: string;
}

export class PromptRefiner {
  async refine(input: RefinementInput): Promise<RefinementResult> {
    const response = await input.adapter.chat([
      { role: 'system', content: 'You are an expert prompt engineer that proposes minimal, safe diffs.' },
      {
        role: 'user',
        content: this.buildPrompt(input.goal, input.rubric, input.prompt.text, input.diagnostics),
      },
    ]);

    const { diff, note } = this.extractDiff(response.text);
    const updatedPrompt = applyUnifiedDiff(input.prompt.text, diff);
    return { diff, note, updatedPrompt };
  }

  private buildPrompt(goal: string, rubric: Rubric, promptText: string, diagnostics: string): string {
    return [
      '# Prompt Refinement Task',
      '',
      '## Goal',
      goal,
      '',
      '## Current Prompt',
      '```',
      promptText,
      '```',
      '',
      '## Rubric',
      JSON.stringify(rubric, null, 2),
      '',
      '## Diagnostics',
      diagnostics,
      '',
      'Return a response formatted as:',
      '<diff>...</diff>',
      '<note>...</note>',
    ].join('\n');
  }

  private extractDiff(raw: string): { diff: string; note: string } {
    const diffMatch = raw.match(/<diff>([\s\S]*?)<\/diff>/);
    const noteMatch = raw.match(/<note>([\s\S]*?)<\/note>/);
    if (!diffMatch) {
      throw new Error('LLM response did not include a diff section');
    }

    return {
      diff: diffMatch[1].trim(),
      note: noteMatch?.[1].trim() ?? 'No rationale provided.',
    };
  }

}

export const promptRefiner = new PromptRefiner();
