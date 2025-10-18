'use client';

import type { Rubric, RubricCriterion } from '@edison/shared';
import { useMemo, useState } from 'react';

interface RubricStepProps {
  defaultRubric?: Rubric;
  onNext: (rubric: Rubric) => void | Promise<void>;
  onBack: () => void;
}

const defaultCriterion: RubricCriterion = {
  name: 'Helpfulness',
  description: 'Answers the user question with concrete next steps.',
  weight: 1,
  scale: { min: 0, max: 5 },
};

export function RubricStep({ defaultRubric, onNext, onBack }: RubricStepProps) {
  const [rubric, setRubric] = useState<Rubric>(defaultRubric ?? [defaultCriterion]);
  const [activeIndex, setActiveIndex] = useState(0);

  const activeCriterion = useMemo(() => rubric[activeIndex], [rubric, activeIndex]);

  const updateCriterion = (updates: Partial<RubricCriterion>) => {
    setRubric((prev) => {
      const copy = [...prev];
      copy[activeIndex] = { ...copy[activeIndex], ...updates };
      return copy;
    });
  };

  const addCriterion = () => {
    const newCriterion: RubricCriterion = {
      name: `Criterion ${rubric.length + 1}`,
      description: 'Describe the behavior you expect.',
      weight: 0,
      scale: { min: 0, max: 5 },
    };
    setRubric((prev) => [...prev, newCriterion]);
    setActiveIndex(rubric.length);
  };

  const weightsTotal = useMemo(() => rubric.reduce((total, criterion) => total + criterion.weight, 0), [rubric]);

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Craft the evaluation rubric</h3>
          <p className="text-sm text-slate-600">Weights should sum to 1.0 so composite scores reflect your priorities.</p>
        </div>
        <button
          className={[
            'inline-flex items-center rounded-lg border border-slate-200',
            'px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50',
          ].join(' ')}
          type="button"
          onClick={addCriterion}
        >
          Add criterion
        </button>
      </header>

      <div className="grid gap-6 md:grid-cols-[220px_1fr]">
        <aside className="space-y-2">
          {rubric.map((criterion, index) => (
            <button
              key={`${criterion.name}-${index}`}
              type="button"
              onClick={() => setActiveIndex(index)}
              className={[
                'w-full rounded-lg border px-3 py-2 text-left text-sm',
                index === activeIndex
                  ? 'border-slate-900 bg-slate-900 text-white'
                  : 'border-slate-200 bg-white text-slate-700',
              ].join(' ')}
            >
              {criterion.name}
            </button>
          ))}
        </aside>

        {activeCriterion && (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Name</label>
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={activeCriterion.name}
                onChange={(event) => updateCriterion({ name: event.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Description</label>
              <textarea
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                rows={3}
                value={activeCriterion.description}
                onChange={(event) => updateCriterion({ description: event.target.value })}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Weight</label>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={activeCriterion.weight}
                  onChange={(event) => updateCriterion({ weight: Number(event.target.value) })}
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Scale min</label>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  type="number"
                  value={activeCriterion.scale.min}
                  onChange={(event) =>
                    updateCriterion({ scale: { ...activeCriterion.scale, min: Number(event.target.value) } })
                  }
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Scale max</label>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  type="number"
                  value={activeCriterion.scale.max}
                  onChange={(event) =>
                    updateCriterion({ scale: { ...activeCriterion.scale, max: Number(event.target.value) } })
                  }
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <footer className="flex items-center justify-between text-sm">
        <button
          className="inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          type="button"
          onClick={onBack}
        >
          Back
        </button>
        <div className="text-xs text-slate-500">Weights total: {weightsTotal.toFixed(2)} (target 1.00)</div>
        <button
          className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          type="button"
          onClick={async () => {
            await onNext(rubric);
          }}
          disabled={Math.abs(weightsTotal - 1) > 0.05}
        >
          Continue
        </button>
      </footer>
    </div>
  );
}
