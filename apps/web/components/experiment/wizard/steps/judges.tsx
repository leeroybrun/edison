'use client';

import { useState } from 'react';

import type { JudgeConfigDraft } from '../wizard';

const PROVIDERS = ['OPENAI', 'ANTHROPIC', 'GOOGLE_VERTEX', 'AWS_BEDROCK', 'AZURE_OPENAI', 'OLLAMA', 'OPENAI_COMPATIBLE'] as const;
const MODES = ['POINTWISE', 'PAIRWISE'] as const;

type Provider = (typeof PROVIDERS)[number];
type JudgeMode = (typeof MODES)[number];

interface JudgesStepProps {
  defaultJudges?: JudgeConfigDraft[];
  onNext: (judges: JudgeConfigDraft[]) => void | Promise<void>;
  onBack: () => void;
}

interface JudgeRow {
  provider: Provider;
  modelId: string;
  mode: JudgeMode;
  systemPrompt: string;
}

export function JudgesStep({ defaultJudges, onNext, onBack }: JudgesStepProps) {
  const initialRows: JudgeRow[] = (defaultJudges && defaultJudges.length > 0)
    ? defaultJudges.map((judge) => ({
        provider: judge.provider as Provider,
        modelId: judge.modelId,
        mode: judge.mode as JudgeMode,
        systemPrompt: judge.systemPrompt,
      }))
    : [createDefaultJudge()];

  const [rows, setRows] = useState<JudgeRow[]>(initialRows);

  const updateRow = (index: number, patch: Partial<JudgeRow>) => {
    setRows((prev) => prev.map((row, idx) => (idx === index ? { ...row, ...patch } : row)));
  };

  const addRow = () => setRows((prev) => [...prev, createDefaultJudge()]);

  const removeRow = (index: number) => {
    setRows((prev) => (prev.length === 1 ? prev : prev.filter((_, idx) => idx !== index)));
  };

  const canContinue = rows.every((row) => row.modelId.trim().length > 0 && row.systemPrompt.trim().length > 20);

  const payload = rows.map<JudgeConfigDraft>((row) => ({
    provider: row.provider,
    modelId: row.modelId,
    mode: row.mode,
    systemPrompt: row.systemPrompt,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Configure judges</h3>
        <p className="text-sm text-slate-600">
          Judges score each output against the rubric. Pairwise judges compare competing outputs to build rankings.
        </p>
      </div>

      <div className="space-y-4">
        {rows.map((row, index) => (
          <div key={index} className="rounded-lg border border-slate-200 p-4">
            <div className="flex items-start justify-between">
              <p className="text-sm font-semibold text-slate-800">Judge {index + 1}</p>
              <button
                className="text-xs font-semibold text-rose-600 disabled:opacity-50"
                type="button"
                onClick={() => removeRow(index)}
                disabled={rows.length === 1}
              >
                Remove
              </button>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Provider</label>
                <select
                  className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                  value={row.provider}
                  onChange={(event) => updateRow(index, { provider: event.target.value as Provider })}
                >
                  {PROVIDERS.map((provider) => (
                    <option key={provider} value={provider}>
                      {provider}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Model ID</label>
                <input
                  className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                  placeholder="gpt-4o-mini"
                  value={row.modelId}
                  onChange={(event) => updateRow(index, { modelId: event.target.value })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Mode</label>
                <select
                  className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                  value={row.mode}
                  onChange={(event) => updateRow(index, { mode: event.target.value as JudgeMode })}
                >
                  {MODES.map((mode) => (
                    <option key={mode} value={mode}>
                      {mode}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label className="text-xs font-medium uppercase tracking-wide text-slate-500">System prompt</label>
                <textarea
                  className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                  rows={4}
                  placeholder="You are an expert evaluator scoring responses against the rubric..."
                  value={row.systemPrompt}
                  onChange={(event) => updateRow(index, { systemPrompt: event.target.value })}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <button
        className="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        type="button"
        onClick={addRow}
      >
        Add judge
      </button>

      <div className="flex justify-between">
        <button
          className="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
          type="button"
          onClick={onBack}
        >
          Back
        </button>
        <button
          className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          type="button"
          disabled={!canContinue}
          onClick={async () => {
            await onNext(payload);
          }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}

function createDefaultJudge(): JudgeRow {
  return {
    provider: 'OPENAI',
    modelId: 'gpt-4o-mini',
    mode: 'POINTWISE',
    systemPrompt:
      'You are an impartial judge. Score the assistant output against each rubric criterion and explain briefly why.',
  };
}
