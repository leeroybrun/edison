'use client';

import type { StopRules } from '@edison/shared';
import { useState } from 'react';

interface StopRulesStepProps {
  defaultStopRules?: StopRules;
  onNext: (stopRules: StopRules) => void | Promise<void>;
  onBack: () => void;
}

const defaultStopRules: StopRules = {
  maxIterations: 5,
  minDeltaThreshold: 0.02,
  maxBudgetUsd: 25,
  maxTotalTokens: 200000,
  convergenceWindow: 3,
};

export function StopRulesStep({ defaultStopRules: provided, onNext, onBack }: StopRulesStepProps) {
  const [rules, setRules] = useState<StopRules>(provided ?? defaultStopRules);

  const update = (updates: Partial<StopRules>) => {
    setRules((prev) => ({ ...prev, ...updates }));
  };

  return (
    <form
      className="space-y-6"
      onSubmit={async (event) => {
        event.preventDefault();
        await onNext(rules);
      }}
    >
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Control iteration cost & pace</h3>
        <p className="text-sm text-slate-600">
          Edison stops automatically when improvements flatten or budgets are exhausted.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Max iterations</span>
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2"
            type="number"
            min={1}
            max={100}
            value={rules.maxIterations}
            onChange={(event) => update({ maxIterations: Number(event.target.value) })}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Min improvement delta</span>
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2"
            type="number"
            step={0.005}
            min={0}
            max={1}
            value={rules.minDeltaThreshold}
            onChange={(event) => update({ minDeltaThreshold: Number(event.target.value) })}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Budget (USD)</span>
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2"
            type="number"
            min={0}
            value={rules.maxBudgetUsd ?? ''}
            onChange={(event) =>
              update({ maxBudgetUsd: event.target.value ? Number(event.target.value) : undefined })
            }
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Token ceiling</span>
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2"
            type="number"
            min={0}
            value={rules.maxTotalTokens ?? ''}
            onChange={(event) =>
              update({ maxTotalTokens: event.target.value ? Number(event.target.value) : undefined })
            }
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Convergence window</span>
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2"
            type="number"
            min={2}
            max={10}
            value={rules.convergenceWindow}
            onChange={(event) => update({ convergenceWindow: Number(event.target.value) })}
          />
        </label>
      </div>

      <footer className="flex items-center justify-between">
        <button
          className="inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          type="button"
          onClick={onBack}
        >
          Back
        </button>
        <button
          className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
          type="submit"
        >
          Finish setup
        </button>
      </footer>
    </form>
  );
}
