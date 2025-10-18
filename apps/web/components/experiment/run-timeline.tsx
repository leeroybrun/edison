'use client';

import { useEffect, useMemo, useState } from 'react';

import { CoverageHeatmap } from './coverage-heatmap';

type CoverageMatrix = Record<string, Record<string, { count: number; avgScore: number }>>;

type SafetySummary = {
  totalOutputs: number;
  flaggedOutputs: number;
  piiFindings: number;
  toxicFindings: number;
  jailbreakFindings: number;
  sampleFindings: Array<{ outputId: string; tags: string[]; issues: string[] }>;
};

type TimelineEvent = {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  timestamp: number;
};

type SnapshotPayload = {
  status: string;
  totalRuns: number;
  completedRuns: number;
  failedRuns: number;
  startedAt: string | null;
  finishedAt: string | null;
  metrics: Record<string, unknown> | null;
};

export function RunTimeline({ iterationId }: { iterationId: string }) {
  const [snapshot, setSnapshot] = useState<SnapshotPayload | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [coverage, setCoverage] = useState<CoverageMatrix | null>(null);
  const [safety, setSafety] = useState<SafetySummary | null>(null);

  const baseUrl = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080',
    [],
  );

  useEffect(() => {
    const source = new EventSource(`${baseUrl}/iterations/${iterationId}/stream`);

    const pushEvent = (type: string, payload: Record<string, unknown>) => {
      setEvents((prev) => [
        ...prev,
        {
          id: `${type}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          type,
          payload,
          timestamp: Date.now(),
        },
      ]);
    };

    source.addEventListener('snapshot', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as SnapshotPayload;
        setSnapshot(data);
        pushEvent('status', { status: data.status });
      } catch (err) {
        console.error('Failed to parse snapshot', err);
      }
    });

    source.addEventListener('status', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as Record<string, unknown>;
        pushEvent('status', data);
      } catch (err) {
        console.error('Failed to parse status event', err);
      }
    });

    source.addEventListener('run-progress', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as Record<string, unknown>;
        pushEvent('run-progress', data);
      } catch (err) {
        console.error('Failed to parse run-progress event', err);
      }
    });

    source.addEventListener('judging-complete', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as Record<string, unknown>;
        pushEvent('judging-complete', data);
      } catch (err) {
        console.error('Failed to parse judging event', err);
      }
    });

    source.addEventListener('metrics', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as Record<string, unknown>;
        setSnapshot((prev) => (prev ? { ...prev, metrics: data } : prev));
        if (data.coverageMatrix) {
          setCoverage(data.coverageMatrix as CoverageMatrix);
        }
        if (data.safetySummary) {
          setSafety(data.safetySummary as SafetySummary);
        }
        pushEvent('metrics', data);
      } catch (err) {
        console.error('Failed to parse metrics event', err);
      }
    });

    source.addEventListener('safety', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as SafetySummary;
        setSafety(data);
        pushEvent('safety', data as unknown as Record<string, unknown>);
      } catch (err) {
        console.error('Failed to parse safety event', err);
      }
    });

    source.addEventListener('refinement', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as Record<string, unknown>;
        pushEvent('refinement', data);
      } catch (err) {
        console.error('Failed to parse refinement event', err);
      }
    });

    source.addEventListener('failure', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as { message?: string };
        const message = data.message ?? 'Iteration failed';
        setError(message);
        pushEvent('failure', data);
      } catch (err) {
        console.error('Failed to parse failure event', err);
      }
    });

    source.onerror = () => {
      setError('Connection lost. Please refresh to resume streaming updates.');
      source.close();
    };

    return () => {
      source.close();
    };
  }, [baseUrl, iterationId]);

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Iteration activity</h2>
          <p className="text-sm text-slate-600">
            Live updates for iteration <span className="font-mono text-xs text-slate-500">{iterationId}</span>
          </p>
        </div>
        {snapshot && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
            <div>Status: {snapshot.status}</div>
            <div>
              Runs: {snapshot.completedRuns}/{snapshot.totalRuns} (failed {snapshot.failedRuns})
            </div>
          </div>
        )}
      </header>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      )}

      <ol className="space-y-3 text-sm">
        {events.map((event) => (
          <li key={event.id} className="flex items-start gap-3">
            <span className="mt-0.5 h-2 w-2 rounded-full bg-teal-500" aria-hidden />
            <div>
              <div className="font-medium text-slate-800">{event.type}</div>
              <pre className="mt-1 overflow-x-auto rounded bg-slate-900/5 p-2 font-mono text-xs text-slate-700">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
              <div className="mt-1 text-xs text-slate-500">
                {new Date(event.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </li>
        ))}
        {events.length === 0 && (
          <li className="rounded-lg border border-dashed border-slate-200 p-4 text-center text-slate-500">
            Waiting for iteration events...
          </li>
        )}
      </ol>

      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">Coverage heatmap</h3>
        {coverage ? <CoverageHeatmap matrix={coverage} /> : <p className="text-sm text-slate-500">Coverage metrics will appear once judgments complete.</p>}
      </section>

      {safety ? (
        <section className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Safety findings</h3>
          <p className="text-sm text-slate-600">
            {safety.flaggedOutputs} of {safety.totalOutputs} outputs flagged. PII: {safety.piiFindings}, Toxic: {safety.toxicFindings}, Jailbreak: {safety.jailbreakFindings}
          </p>
          {safety.sampleFindings.length > 0 && (
            <ul className="space-y-2 text-xs text-slate-600">
              {safety.sampleFindings.map((finding) => (
                <li key={finding.outputId} className="rounded border border-slate-200 bg-slate-50 p-2">
                  <div className="font-medium text-slate-800">Output {finding.outputId}</div>
                  <div>Tags: {finding.tags.join(', ') || 'untagged'}</div>
                  <div>Issues: {finding.issues.join(', ')}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
    </section>
  );
}
