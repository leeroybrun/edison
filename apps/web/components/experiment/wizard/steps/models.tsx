'use client';

import type { ModelParams } from '@edison/shared';
import { useState } from 'react';

import type { ModelConfigDraft } from '../wizard';

const PROVIDERS = ['OPENAI', 'ANTHROPIC', 'GOOGLE_VERTEX', 'AWS_BEDROCK', 'AZURE_OPENAI', 'OLLAMA', 'OPENAI_COMPATIBLE'] as const;

type Provider = (typeof PROVIDERS)[number];

interface ModelsStepProps {
  defaultModels?: ModelConfigDraft[];
  onNext: (models: ModelConfigDraft[]) => void | Promise<void>;
  onBack: () => void;
}

interface ModelRow {
  provider: Provider;
  modelId: string;
  temperature: string;
  maxTokens: string;
  seed: string;
}

export function ModelsStep({ defaultModels, onNext, onBack }: ModelsStepProps) {
  const initialRows: ModelRow[] = (defaultModels && defaultModels.length > 0)
    ? defaultModels.map((model) => ({
        provider: (model.provider as Provider) ?? 'OPENAI',
        modelId: model.modelId,
        temperature: model.params.temperature?.toString() ?? '0.7',
        maxTokens: model.params.maxTokens?.toString() ?? '',
        seed: model.seed?.toString() ?? '',
      }))
    : [createEmptyRow()];

  const [rows, setRows] = useState<ModelRow[]>(initialRows);

  const updateRow = (index: number, patch: Partial<ModelRow>) => {
    setRows((prev) => prev.map((row, idx) => (idx === index ? { ...row, ...patch } : row)));
  };

  const addRow = () => {
    setRows((prev) => [...prev, createEmptyRow()]);
  };

  const removeRow = (index: number) => {
    setRows((prev) => (prev.length === 1 ? prev : prev.filter((_, idx) => idx !== index)));
  };

  const canContinue = rows.every((row) => row.modelId.trim().length > 0);

  const buildPayload = (): ModelConfigDraft[] =>
    rows.map<ModelConfigDraft>((row) => ({
      provider: row.provider,
      modelId: row.modelId,
      params: normaliseParams({
        temperature: row.temperature,
        maxTokens: row.maxTokens,
      }),
      seed: row.seed.trim() ? Number(row.seed) : undefined,
    }));

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Choose execution models</h3>
        <p className="text-sm text-slate-600">
          Edison will fan out each iteration across these provider/model combinations. Configure deterministic seeds and sampling
          to balance exploration vs. exploitation.
        </p>
      </div>

      <div className="space-y-4">
        {rows.map((row, index) => (
          <div key={index} className="rounded-lg border border-slate-200 p-4">
            <div className="flex items-start justify-between">
              <p className="text-sm font-semibold text-slate-800">Model {index + 1}</p>
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
                  placeholder="gpt-4o"
                  value={row.modelId}
                  onChange={(event) => updateRow(index, { modelId: event.target.value })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Temperature</label>
                <input
                  className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                  placeholder="0.7"
                  value={row.temperature}
                  onChange={(event) => updateRow(index, { temperature: event.target.value })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Max tokens</label>
                <input
                  className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                  placeholder="1024"
                  value={row.maxTokens}
                  onChange={(event) => updateRow(index, { maxTokens: event.target.value })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Seed (optional)</label>
                <input
                  className="w-full rounded-lg border border-slate-200 p-2 text-sm"
                  placeholder="42"
                  value={row.seed}
                  onChange={(event) => updateRow(index, { seed: event.target.value })}
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
        Add model
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
            await onNext(buildPayload());
          }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}

function createEmptyRow(): ModelRow {
  return {
    provider: 'OPENAI',
    modelId: '',
    temperature: '0.7',
    maxTokens: '',
    seed: '',
  };
}

function normaliseParams(input: { temperature: string; maxTokens: string }): Partial<ModelParams> {
  const params: Partial<ModelParams> = {};
  const temperature = Number(input.temperature);
  if (!Number.isNaN(temperature)) {
    params.temperature = temperature;
  }
  const maxTokens = Number(input.maxTokens);
  if (!Number.isNaN(maxTokens) && maxTokens > 0) {
    params.maxTokens = Math.round(maxTokens);
  }
  return params;
}
