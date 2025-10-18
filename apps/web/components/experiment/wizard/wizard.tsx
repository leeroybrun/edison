'use client';

import type { FewShotExample, ModelParams, Rubric, StopRules } from '@edison/shared';
import { useState, type ReactNode } from 'react';

import { DatasetStep } from './steps/datasets';
import { JudgesStep } from './steps/judges';
import { ModelsStep } from './steps/models';
import { ObjectiveStep } from './steps/objective';
import { PromptStep } from './steps/prompt';
import { RubricStep } from './steps/rubric';
import { StopRulesStep } from './steps/stop-rules';

import { buildAuthHeaders } from '@/lib/auth-client';

export interface ModelConfigDraft {
  provider: string;
  modelId: string;
  params: Partial<ModelParams>;
  seed?: number;
}

export interface JudgeConfigDraft {
  provider: string;
  modelId: string;
  mode: 'POINTWISE' | 'PAIRWISE';
  systemPrompt: string;
}

export interface PromptDraft {
  name: string;
  systemText?: string;
  text: string;
  fewShots?: FewShotExample[];
}

export interface WizardState {
  projectId: string;
  name: string;
  goal: string;
  rubric: Rubric;
  prompt: PromptDraft;
  datasetIds: string[];
  modelConfigs: ModelConfigDraft[];
  judgeConfigs: JudgeConfigDraft[];
  stopRules: StopRules;
}

const stepOrder = ['objective', 'rubric', 'prompt', 'datasets', 'models', 'judges', 'stop'] as const;

type StepKey = (typeof stepOrder)[number];

export function ExperimentWizard({ projectId }: { projectId: string }) {
  const [state, setState] = useState<Partial<WizardState>>({ projectId });
  const [step, setStep] = useState<StepKey>('objective');
  const [submitted, setSubmitted] = useState(false);

  const goToNext = async (payload: Partial<WizardState>) => {
    setState((prev) => ({ ...prev, ...payload }));
    const currentIndex = stepOrder.indexOf(step);
    const nextStep = stepOrder[currentIndex + 1];

    if (nextStep) {
      setStep(nextStep);
      return;
    }

    if (!submitted) {
      try {
        await submitExperiment({ ...state, ...payload, projectId });
        setSubmitted(true);
      } catch (error) {
        console.error('Failed to submit experiment', error);
      }
    }
  };

  const goToPrevious = () => {
    const currentIndex = stepOrder.indexOf(step);
    const previousStep = stepOrder[currentIndex - 1];
    if (previousStep) {
      setStep(previousStep);
    }
  };

  let content: ReactNode;
  if (submitted) {
    content = <SubmissionSummary />;
  } else if (step === 'objective') {
    content = (
      <ObjectiveStep
        defaultGoal={state.goal}
        defaultName={state.name}
        onNext={({ goal, name }) => goToNext({ goal, name })}
      />
    );
  } else if (step === 'rubric') {
    content = (
      <RubricStep
        defaultRubric={state.rubric}
        onNext={(rubric) => goToNext({ rubric })}
        onBack={goToPrevious}
      />
    );
  } else if (step === 'prompt') {
    content = (
      <PromptStep
        defaultPrompt={state.prompt}
        onNext={(prompt) => goToNext({ prompt })}
        onBack={goToPrevious}
      />
    );
  } else if (step === 'datasets') {
    content = (
      <DatasetStep
        projectId={projectId}
        defaultDatasetIds={state.datasetIds}
        onNext={(datasetIds) => goToNext({ datasetIds })}
        onBack={goToPrevious}
      />
    );
  } else if (step === 'models') {
    content = (
      <ModelsStep
        defaultModels={state.modelConfigs}
        onNext={(modelConfigs) => goToNext({ modelConfigs })}
        onBack={goToPrevious}
      />
    );
  } else if (step === 'judges') {
    content = (
      <JudgesStep
        defaultJudges={state.judgeConfigs}
        onNext={(judgeConfigs) => goToNext({ judgeConfigs })}
        onBack={goToPrevious}
      />
    );
  } else {
    content = (
      <StopRulesStep
        defaultStopRules={state.stopRules}
        onNext={(stopRules) => goToNext({ stopRules })}
        onBack={goToPrevious}
      />
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-900">New experiment wizard</h2>
        <p className="text-xs uppercase tracking-wider text-slate-500">
          Step {submitted ? stepOrder.length : stepOrder.indexOf(step) + 1} of {stepOrder.length}
        </p>
      </div>
      <div className="mt-6">{content}</div>
    </div>
  );
}

async function submitExperiment(state: Partial<WizardState>) {
  if (
    !state.goal ||
    !state.rubric ||
    !state.stopRules ||
    !state.projectId ||
    !state.name ||
    !state.prompt ||
    !state.datasetIds ||
    !state.modelConfigs ||
    !state.judgeConfigs
  ) {
    throw new Error('Wizard state incomplete');
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';
  const payload = {
    id: 0,
    json: {
      projectId: state.projectId,
      name: state.name,
      description: state.goal,
      goal: state.goal,
      rubric: state.rubric,
      stopRules: state.stopRules,
      datasetIds: state.datasetIds,
      prompt: state.prompt,
      modelConfigs: state.modelConfigs,
      judgeConfigs: state.judgeConfigs,
    },
  };

  const response = await fetch(`${baseUrl}/trpc/experiment.create`, {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to create experiment: ${message}`);
  }
}

function SubmissionSummary() {
  return (
    <div className="space-y-3 text-sm text-slate-600">
      <p className="font-medium text-slate-900">Experiment drafted.</p>
      <p>
        Edison stored your objective, rubric, seed prompt, datasets, model fleet, judge configs, and stop rules. The next
        iteration will execute as soon as you supply credentials and launch from the experiment overview.
      </p>
    </div>
  );
}
