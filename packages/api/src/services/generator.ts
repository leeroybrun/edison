import { DatasetCaseSchema } from '@edison/shared';
import type { PrismaClient } from '@prisma/client';
import { z } from 'zod';

import { LLMAdapterFactory } from '../llm/factory';

const SyntheticCaseSchema = DatasetCaseSchema.extend({
  input: z.record(z.string(), z.unknown()),
});

type SyntheticCase = z.infer<typeof SyntheticCaseSchema>;

export class GeneratorService {
  constructor(private readonly prisma: PrismaClient, private readonly adapterFactory: LLMAdapterFactory) {}

  async generateSyntheticDataset(
    projectId: string,
    spec: { count: number; diversity: number; domainHints: string },
    datasetId?: string,
  ): Promise<string> {
    let dataset = datasetId
      ? await this.prisma.dataset.findUniqueOrThrow({ where: { id: datasetId, projectId } })
      : await this.prisma.dataset.create({
          data: {
            projectId,
            name: `Synthetic ${new Date().toISOString()}`,
            kind: 'SYNTHETIC',
            metadata: { ...spec, status: 'pending' },
          },
        });

    if (datasetId) {
      dataset = await this.prisma.dataset.update({
        where: { id: dataset.id },
        data: {
          metadata: { ...(dataset.metadata as Record<string, unknown> | null) ?? {}, ...spec, status: 'pending' },
        },
      });
      await this.prisma.case.deleteMany({ where: { datasetId: dataset.id } });
    }

    const result = await this.generateCasesWithFallback(projectId, spec);

    await this.prisma.case.createMany({
      data: result.cases.map((item) => ({
        datasetId: dataset.id,
        input: item.input,
        expected: item.expected ?? null,
        tags: item.tags ?? [],
        difficulty: item.difficulty ?? 3,
        metadata: item.metadata ?? {},
      })),
    });

    await this.prisma.dataset.update({
      where: { id: dataset.id },
      data: {
        metadata: {
          ...(dataset.metadata as Record<string, unknown> | null) ?? {},
          spec,
          discarded: result.discarded,
          status: 'ready',
          generatedAt: new Date().toISOString(),
          generator: result.source,
        },
      },
    });

    return dataset.id;
  }

  private async generateCasesWithFallback(
    projectId: string,
    spec: { count: number; diversity: number; domainHints: string },
  ): Promise<{ cases: SyntheticCase[]; discarded: number; source: 'llm' | 'fallback' }> {
    try {
      const credential = await this.adapterFactory.getCredentialForProject(projectId, 'OPENAI');
      const adapter = await this.adapterFactory.getAdapter(credential, 'gpt-4o-mini');

      const response = await adapter.chat([
        {
          role: 'user',
          content: `Generate ${spec.count} diverse JSON test cases for this prompt domain: ${spec.domainHints}. Diversity: ${spec.diversity}.`,
        },
      ]);

      const parsed = parseSyntheticCasePayload(response.text, spec.count);
      return { ...parsed, source: 'llm' };
    } catch (error) {
      const fallbackCases = buildFallbackCases(spec);
      return { cases: fallbackCases, discarded: 0, source: 'fallback' };
    }
  }
}

export function parseSyntheticCasePayload(raw: string, limit: number): { cases: SyntheticCase[]; discarded: number } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    throw new Error('LLM response was not valid JSON');
  }

  if (!Array.isArray(parsed)) {
    throw new Error('LLM response must be a JSON array of test cases');
  }

  const cases: SyntheticCase[] = [];
  const seen = new Set<string>();
  let discarded = 0;

  for (const candidate of parsed) {
    const result = SyntheticCaseSchema.safeParse(candidate);
    if (!result.success) {
      discarded += 1;
      continue;
    }

    const normalized: SyntheticCase = {
      ...result.data,
      tags: Array.from(new Set(result.data.tags ?? [])),
    };

    const dedupeKey = JSON.stringify({
      input: normalized.input,
      expected: normalized.expected ?? null,
    });

    if (seen.has(dedupeKey)) {
      discarded += 1;
      continue;
    }

    seen.add(dedupeKey);
    cases.push(normalized);

    if (cases.length >= limit) {
      break;
    }
  }

  if (cases.length === 0) {
    throw new Error('LLM response did not contain any valid test cases');
  }

  return { cases, discarded };
}

function buildFallbackCases(spec: { count: number; diversity: number; domainHints: string }): SyntheticCase[] {
  const hints = spec.domainHints.split(/[,.;\n]/).map((segment) => segment.trim()).filter(Boolean);
  const archetypes = hints.length > 0 ? hints : ['general scenario'];
  const difficulties = [1, 2, 3, 4, 5];

  const cases: SyntheticCase[] = [];
  for (let index = 0; index < spec.count; index += 1) {
    const topic = archetypes[index % archetypes.length];
    const difficulty = difficulties[index % difficulties.length];
    const id = index + 1;
    cases.push({
      input: {
        user_message: `Scenario ${id}: ${topic} with nuance level ${difficulty}. Provide a thorough answer addressing policy, tone, and next steps.`,
        metadata: {
          segment: topic,
          variant: id % 2 === 0 ? 'edge-case' : 'happy-path',
        },
      },
      expected: null,
      tags: [`${topic.toLowerCase().replace(/\s+/g, '-')}`, difficulty >= 4 ? 'challenging' : 'standard'],
      difficulty,
      metadata: {
        generatedBy: 'fallback-synthesiser',
      },
    });
  }

  return cases;
}
