'use client';

import { useState } from 'react';

interface ObjectiveStepProps {
  defaultGoal?: string;
  defaultName?: string;
  onNext: (payload: { name: string; goal: string }) => void | Promise<void>;
}

export function ObjectiveStep({ defaultGoal, defaultName, onNext }: ObjectiveStepProps) {
  const [goal, setGoal] = useState(defaultGoal ?? '');
  const [name, setName] = useState(defaultName ?? '');

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Define the objective</h3>
        <p className="text-sm text-slate-600">
          Capture the user intent, constraints, and success criteria in a single paragraph.
        </p>
      </div>
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700" htmlFor="experiment-name">
          Experiment name
        </label>
        <input
          id="experiment-name"
          className="w-full rounded-lg border border-slate-200 p-3 text-sm"
          placeholder="Customer support empathy v1"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <textarea
        className="w-full rounded-lg border border-slate-200 p-3 text-sm"
        rows={6}
        placeholder="Example: Generate empathetic customer support replies that follow our policy library and deflect malicious requests."
        value={goal}
        onChange={(event) => setGoal(event.target.value)}
      />
      <div className="flex justify-end">
        <button
          className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          type="button"
          onClick={async () => {
            await onNext({ name, goal });
          }}
          disabled={goal.trim().length < 10 || name.trim().length < 3}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
