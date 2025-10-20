import { RubricSchema } from '@edison/shared';
import type { PromptConfig, Rubric, RubricCriterion } from '@edison/shared';
import { z } from 'zod';

import { LLMAdapterFactory } from '../llm/factory';
import type { LLMAdapter } from '../llm/types';

const DraftObjectivesSchema = z.object({
  options: z.array(z.object({ title: z.string(), text: z.string() })).min(1),
});

const DraftPromptsSchema = z.object({
  prompts: z
    .array(
      z.object({
        name: z.string(),
        text: z.string(),
        systemText: z.string().optional(),
        rationale: z.string(),
      }),
    )
    .min(1),
});

const ImprovePromptSchema = z.object({ improved: z.string(), changes: z.string() });

function createFallbackObjectives(hints: string, count: number): { options: { title: string; text: string }[] } {
  return {
    options: Array.from({ length: count }, (_, index) => ({
      title: `Objective ${index + 1}`,
      text: `${hints.trim()} — focus ${index + 1} on clarifying success metrics and user constraints.`,
    })),
  };
}

function createFallbackPrompts(objective: string, rubric: Rubric, count: number) {
  return {
    prompts: Array.from({ length: count }, (_, index) => ({
      name: `Prompt v${index + 1}`,
      text: `# Objective\n${objective}\n\n# Instructions\n- Address: ${rubric.map((item: RubricCriterion) => item.name).join(', ')}\n- Provide a concise, structured answer.`,
      rationale: 'Generated fallback prompt emphasising rubric criteria.',
    })),
  };
}

function createFallbackImprovement(promptText: string) {
  return {
    improved: `${promptText}\n\n# Clarifications\n- Add explicit success criteria.\n- Ensure responses cite supporting details when available.`,
    changes: 'Appended clarifying guidance to improve determinism and evaluation alignment.',
  };
}

export class AIAssistService {
  constructor(private readonly factory: LLMAdapterFactory) {}

  async draftObjectives(
    hints: string,
    count: number,
    projectId?: string,
  ): Promise<{ options: { title: string; text: string }[] }> {
    const fallback = () => createFallbackObjectives(hints, count);
    const adapter = await this.resolveAdapter(projectId, 'gpt-4o-mini');
    if (!adapter) {
      return fallback();
    }

    try {
      const response = await adapter.chat(
        [
          { role: 'system', content: 'You help product teams articulate crisp experiment objectives.' },
          {
            role: 'user',
            content: `Using the following hints, propose ${count} objectives for a prompt experiment. Return JSON: {"options": [{"title": string, "text": string}]}.\n\nHints:\n${hints}`,
          },
        ],
        { params: { temperature: 0.6 } },
      );
      const parsed = DraftObjectivesSchema.parse(JSON.parse(response.text));
      return parsed;
    } catch (error) {
      return fallback();
    }
  }

  async draftRubric(objective: string, projectId?: string): Promise<{ criteria: Rubric }> {
    const fallbackRubric: Rubric = [
      { name: 'Helpfulness', description: 'Addresses the user request directly with actionable detail.', weight: 0.4, scale: { min: 1, max: 5 } },
      { name: 'Accuracy', description: 'Information is correct and consistent with known facts.', weight: 0.3, scale: { min: 1, max: 5 } },
      { name: 'Clarity', description: 'Response is easy to understand and well-structured.', weight: 0.2, scale: { min: 1, max: 5 } },
      { name: 'Tone', description: 'Appropriate tone for the scenario.', weight: 0.1, scale: { min: 1, max: 5 } },
    ];

    const adapter = await this.resolveAdapter(projectId, 'gpt-4o-mini');
    if (!adapter) {
      return { criteria: fallbackRubric };
    }

    try {
      const response = await adapter.chat(
        [
          { role: 'system', content: 'You design evaluation rubrics for LLM prompt experiments.' },
          {
            role: 'user',
            content: `Objective: ${objective}\n\nReturn a JSON array of rubric criteria where weights sum to 1. Each element: {"name": string, "description": string, "weight": number, "scale": {"min": number, "max": number}}`,
          },
        ],
        { params: { temperature: 0.5 } },
      );
      const parsed = RubricSchema.parse(JSON.parse(response.text));
      return { criteria: parsed };
    } catch (error) {
      return { criteria: fallbackRubric };
    }
  }

  async draftPrompts(
    objective: string,
    rubric: Rubric,
    count: number,
    projectId?: string,
  ): Promise<{ prompts: Array<{ name: string; text: string; systemText?: string; rationale: string }> }> {
    const fallback = () => createFallbackPrompts(objective, rubric, count);
    const adapter = await this.resolveAdapter(projectId, 'gpt-4o');
    if (!adapter) {
      return fallback();
    }

    try {
      const response = await adapter.chat(
        [
          { role: 'system', content: 'You write high-quality prompt drafts for production LLM workflows.' },
          {
            role: 'user',
            content: `Objective: ${objective}\nRubric: ${JSON.stringify(rubric)}\n\nReturn JSON {"prompts": [{"name": string, "text": string, "systemText"?: string, "rationale": string}]}. Provide ${count} options.`,
          },
        ],
        { params: { temperature: 0.8 } },
      );
      const parsed = DraftPromptsSchema.parse(JSON.parse(response.text));
      return parsed;
    } catch (error) {
      return fallback();
    }
  }

  async improvePrompt(
    prompt: Pick<PromptConfig, 'text'>,
    objective: string,
    focus: string[] | undefined,
    projectId?: string,
  ): Promise<{ improved: string; changes: string }> {
    const fallback = () => createFallbackImprovement(prompt.text);
    const adapter = await this.resolveAdapter(projectId, 'gpt-4o');
    if (!adapter) {
      return fallback();
    }

    try {
      const response = await adapter.chat(
        [
          { role: 'system', content: 'You refine prompts with minimal, targeted edits.' },
          {
            role: 'user',
            content: `Objective: ${objective}\nFocus areas: ${(focus ?? ['overall quality']).join(', ')}\n\nPrompt:\n${prompt.text}\n\nReturn JSON {"improved": string, "changes": string}`,
          },
        ],
        { params: { temperature: 0.4 } },
      );
      const parsed = ImprovePromptSchema.parse(JSON.parse(response.text));
      return parsed;
    } catch (error) {
      return fallback();
    }
  }

  private async resolveAdapter(projectId: string | undefined, modelId: string): Promise<LLMAdapter | null> {
    if (projectId) {
      const projectAdapter = await this.factory.tryGetAdapterForProject(projectId, 'OPENAI', modelId);
      if (projectAdapter) {
        return projectAdapter;
      }
    }

    return this.factory.tryGetGlobalAdapter('OPENAI', modelId);
  }
}
