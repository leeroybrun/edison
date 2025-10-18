'use client';

import { useCallback, useEffect, useState } from 'react';

import { buildAuthHeaders } from '@/lib/auth-client';

interface DatasetSummary {
  id: string;
  name: string;
  kind: string;
  description?: string | null;
  cases?: { id: string }[];
}

interface DatasetStepProps {
  projectId: string;
  defaultDatasetIds?: string[];
  onNext: (datasetIds: string[]) => void | Promise<void>;
  onBack: () => void;
}

export function DatasetStep({ projectId, defaultDatasetIds, onNext, onBack }: DatasetStepProps) {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(defaultDatasetIds ?? []));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';
      const response = await fetch(`${baseUrl}/trpc/dataset.list`, {
        method: 'POST',
        headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ id: 0, json: { projectId } }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const payload = await response.json();
      const data = (payload?.result?.data ?? []) as DatasetSummary[];
      setDatasets(data);
      if (data.length > 0) {
        setSelected((prev) => {
          if (prev.size > 0) {
            return prev;
          }
          return new Set(data.slice(0, 1).map((dataset) => dataset.id));
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load datasets');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void fetchDatasets();
  }, [fetchDatasets]);

  const toggleDataset = (datasetId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(datasetId)) {
        next.delete(datasetId);
      } else {
        next.add(datasetId);
      }
      return next;
    });
  };

  const canContinue = selected.size > 0 && !loading;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Select datasets</h3>
        <p className="text-sm text-slate-600">
          Choose the evaluation datasets Edison will use for automated runs. Add synthetic or adversarial sets later from the
          dashboard.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Loading datasets…</p>
      ) : error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          Failed to load datasets: {error}
        </div>
      ) : datasets.length === 0 ? (
        <p className="text-sm text-slate-500">No datasets exist yet for this project. Create one before starting an experiment.</p>
      ) : (
        <div className="space-y-3">
          {datasets.map((dataset) => {
            const checked = selected.has(dataset.id);
            const caseCount = dataset.cases?.length ?? 0;
            return (
              <label
                key={dataset.id}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm ${checked ? 'border-slate-900 bg-slate-900/5' : 'border-slate-200'}`}
              >
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={checked}
                  onChange={() => toggleDataset(dataset.id)}
                />
                <div className="space-y-1">
                  <p className="font-semibold text-slate-900">{dataset.name}</p>
                  <p className="text-xs uppercase tracking-wide text-slate-500">{dataset.kind}</p>
                  {dataset.description ? (
                    <p className="text-xs text-slate-500">{dataset.description}</p>
                  ) : null}
                  <p className="text-xs text-slate-400">{caseCount} cases</p>
                </div>
              </label>
            );
          })}
        </div>
      )}

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
            await onNext(Array.from(selected));
          }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
