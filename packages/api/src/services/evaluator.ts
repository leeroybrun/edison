import type { Rubric } from '@edison/shared';
import { JudgmentResultSchema } from '@edison/shared';
import type { Case, JudgeConfig, Output, Prisma, PrismaClient } from '@prisma/client';
import { z } from 'zod';

import { LLMAdapterFactory } from '../llm/factory';
import { asJsonObject, asJsonValue } from '../lib/json';


type OutputWithCase = Output & { case: Case };

type IterationForJudging = Prisma.IterationGetPayload<{
  include: {
    experiment: {
      include: {
        judgeConfigs: true;
      };
    };
    modelRuns: {
      include: {
        outputs: {
          include: {
            case: true;
          };
        };
      };
    };
  };
}>;

const PairwiseResultSchema = z.object({
  winner: z.enum(['A', 'B']),
  rationale: z.string().min(1),
});

export class EvaluatorService {
  constructor(private readonly prisma: PrismaClient, private readonly adapterFactory: LLMAdapterFactory) {}

  async judgeIteration(iterationId: string): Promise<void> {
    const iteration = (await this.prisma.iteration.findUniqueOrThrow({
      where: { id: iterationId },
      include: {
        experiment: {
          include: {
            judgeConfigs: { where: { isActive: true } },
          },
        },
        modelRuns: {
          include: {
            outputs: {
              include: {
                case: true,
              },
            },
          },
        },
      },
    })) as IterationForJudging;

    const outputs = iteration.modelRuns.flatMap((run) => run.outputs);
    await Promise.all(iteration.experiment.judgeConfigs.map((judge) => this.judgeOutputs(outputs, iteration, judge)));
  }

  private async judgeOutputs(outputs: OutputWithCase[], iteration: IterationForJudging, judge: JudgeConfig): Promise<void> {
    if (judge.mode === 'POINTWISE') {
      await Promise.all(outputs.map((output) => this.judgePointwise(output, iteration, judge)));
    } else {
      await this.judgePairwise(outputs, iteration, judge);
    }
  }

  private async judgePointwise(output: OutputWithCase, iteration: IterationForJudging, judge: JudgeConfig): Promise<void> {
    const credential = await this.adapterFactory.getCredentialForProject(iteration.experiment.projectId, judge.provider);
    const adapter = await this.adapterFactory.getAdapter(credential, judge.modelId);
    const rubric = iteration.experiment.rubric as Rubric;
    const prompt = this.buildPointwisePrompt(iteration.experiment.goal, rubric, output.case.input, output.rawText);

    const response = await adapter.chat(
      [
        { role: 'system', content: judge.systemPrompt },
        { role: 'user', content: prompt },
      ],
      { params: { temperature: 0.2 }, seed: 42 },
    );

    const parsed = JudgmentResultSchema.parse(JSON.parse(response.text));

    await this.prisma.judgment.upsert({
      where: {
        outputId_judgeConfigId: {
          outputId: output.id,
          judgeConfigId: judge.id,
        },
      },
      update: {
        scores: asJsonValue(parsed.scores),
        rationales: asJsonValue(parsed.rationales),
        safetyFlags: asJsonValue(parsed.safetyFlags ?? {}),
      },
      create: {
        outputId: output.id,
        judgeConfigId: judge.id,
        mode: judge.mode,
        scores: asJsonValue(parsed.scores),
        rationales: asJsonValue(parsed.rationales),
        safetyFlags: asJsonValue(parsed.safetyFlags ?? {}),
      },
    });
  }

  private async judgePairwise(outputs: OutputWithCase[], iteration: IterationForJudging, judge: JudgeConfig): Promise<void> {
    if (outputs.length < 2) {
      return;
    }

    const credential = await this.adapterFactory.getCredentialForProject(iteration.experiment.projectId, judge.provider);
    const adapter = await this.adapterFactory.getAdapter(credential, judge.modelId);
    const rubric = iteration.experiment.rubric as Rubric;

    for (const output of outputs) {
      const competitors = outputs.filter((candidate) => candidate.caseId === output.caseId && candidate.id !== output.id);
      for (const competitor of competitors) {
        if (output.id > competitor.id) {
          continue;
        }
        const prompt = this.buildPairwisePrompt(iteration.experiment.goal, rubric, output, competitor);
        const response = await adapter.chat(
          [
            { role: 'system', content: judge.systemPrompt },
            { role: 'user', content: prompt },
          ],
          { params: { temperature: 0.2 }, seed: 99 },
        );

        const payload = PairwiseResultSchema.parse(JSON.parse(response.text));
        const winnerOutputId = payload.winner === 'A' ? output.id : competitor.id;

        await this.prisma.judgment.create({
          data: {
            outputId: output.id,
            judgeConfigId: judge.id,
            mode: judge.mode,
            scores: asJsonObject({}),
            rationales: asJsonValue({ overall: payload.rationale }),
            safetyFlags: asJsonObject({}),
            winnerOutputId,
            metadata: asJsonObject({
              competitorOutputId: competitor.id,
              competitorModelRunId: competitor.modelRunId,
            }),
          },
        });
      }
    }
  }

  private buildPointwisePrompt(goal: string, rubric: Rubric, input: unknown, output: string): string {
    return `# Evaluation Task\n\n## Goal\n${goal}\n\n## Rubric\n${JSON.stringify(rubric, null, 2)}\n\n## Input\n${JSON.stringify(input, null, 2)}\n\n## Output\n${output}\n\nRespond with strict JSON following this schema:\n{\n  "scores": { "<criterion>": number },\n  "rationales": { "<criterion>": "string" },\n  "safetyFlags": {\n    "policyViolation": boolean,\n    "piiDetected": boolean,\n    "toxicContent": boolean,\n    "jailbreakAttempt": boolean\n  }\n}`;
  }

  private buildPairwisePrompt(goal: string, rubric: Rubric, outputA: OutputWithCase, outputB: OutputWithCase): string {
    return `# Pairwise Evaluation\n\n## Goal\n${goal}\n\n## Rubric\n${JSON.stringify(rubric, null, 2)}\n\n## Input\n${JSON.stringify(outputA.case.input, null, 2)}\n\n## Output A\n${outputA.rawText}\n\n## Output B\n${outputB.rawText}\n\nRespond with JSON: { "winner": "A"|"B", "rationale": "..." }`;
  }
}
