import { cookies } from 'next/headers';
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';

import { CoverageHeatmap } from '@/components/experiment/coverage-heatmap';
import { ReviewSuggestionCard } from '@/components/experiment/review-suggestion-card';
import { RunOutputViewer } from '@/components/experiment/run-output-viewer';
import { RunTimeline } from '@/components/experiment/run-timeline';

interface ExperimentSummary {
  id: string;
  name: string;
  goal: string;
  status: string;
}

interface IterationSummary {
  id: string;
  number: number;
  status: string;
  startedAt: string | null;
  finishedAt: string | null;
}

interface SuggestionRecord {
  id: string;
  note: string | null;
  diffUnified: string;
  targetCriteria: string[];
  createdAt: string;
  promptVersion: { id: string; version: number; text: string };
}

interface JudgeRecord {
  judgeConfigId: string;
  scores: Record<string, number>;
  rationales?: Record<string, string>;
}

interface OutputRecord {
  id: string;
  rawText: string;
  createdAt: string;
  case: { id: string; input: Record<string, unknown>; tags: string[]; difficulty: number | null };
  judgments: JudgeRecord[];
}

interface ModelRunRecord {
  id: string;
  modelConfig: { modelId: string; provider: string };
  outputs: OutputRecord[];
}

interface IterationDetail {
  id: string;
  metrics: Record<string, unknown> | null;
  modelRuns: ModelRunRecord[];
}

async function callTrpc<T>(path: string, input: unknown, token: string): Promise<T | null> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';
  const response = await fetch(`${baseUrl}/trpc/${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ id: 0, json: input }),
    cache: 'no-store',
  });

  if (!response.ok) {
    console.error(`Failed to fetch ${path}`, await response.text());
    return null;
  }

  const payload = await response.json();
  return (payload?.result?.data?.json ?? payload?.result?.data ?? null) as T | null;
}

export default async function ExperimentDetailPage({ params }: { params: { experimentId: string } }) {
  const token = cookies().get('edison_token')?.value;
  if (!token) {
    redirect('/login');
  }

  const experiment = await callTrpc<ExperimentSummary>('experiment.get', { id: params.experimentId }, token);
  if (!experiment) {
    notFound();
  }

  const iterations = (await callTrpc<IterationSummary[]>(
    'run.listByExperiment',
    { experimentId: params.experimentId },
    token,
  )) ?? [];
  const suggestions = (await callTrpc<SuggestionRecord[]>(
    'review.listSuggestions',
    { experimentId: params.experimentId },
    token,
  )) ?? [];

  const latestIterationSummary = iterations[0] ?? null;
  const iterationDetail = latestIterationSummary
    ? await callTrpc<IterationDetail>('run.get', { iterationId: latestIterationSummary.id }, token)
    : null;

  const outputs = iterationDetail
    ? iterationDetail.modelRuns.flatMap((run) =>
        run.outputs.map((output) => ({
          id: output.id,
          rawText: output.rawText,
          createdAt: output.createdAt,
          case: output.case,
          judgments: output.judgments,
          modelRun: { modelConfig: run.modelConfig },
        })),
      )
    : [];

  const latestMetrics = iterationDetail?.metrics ?? {};
  const budgetStatus = (latestMetrics?.budgetStatus as Record<string, unknown> | undefined) ?? undefined;
  const coverageMatrix = (latestMetrics?.coverageMatrix as Record<string, Record<string, { count: number; avgScore: number }>> | undefined) ?? {};

  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-start justify-between gap-6">
        <div className="space-y-2">
          <Link className="text-sm font-medium text-teal-600" href="/projects">
            ← Back to experiments
          </Link>
          <h1 className="text-3xl font-semibold text-slate-900">{experiment.name}</h1>
          <p className="max-w-3xl text-sm text-slate-600">{experiment.goal}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600 shadow-sm">
          <p>
            <span className="font-semibold text-slate-900">Status:</span> {latestIterationSummary?.status ?? experiment.status}
          </p>
          {latestIterationSummary ? (
            <p>
              <span className="font-semibold text-slate-900">Last iteration:</span> #{latestIterationSummary.number}
            </p>
          ) : null}
          {budgetStatus ? (
            <p>
              <span className="font-semibold text-slate-900">Budget used:</span>{' '}
              {budgetStatus.percentUsed ? `${Math.round((budgetStatus.percentUsed as number) * 100)}%` : 'n/a'}
            </p>
          ) : null}
        </div>
      </header>

      {latestIterationSummary ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <header className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Live iteration timeline</h2>
              <p className="text-sm text-slate-600">
                Observe orchestration lifecycle, safety checks, judging, and refinements as they progress.
              </p>
            </div>
          </header>
          <div className="mt-6">
            <RunTimeline iterationId={latestIterationSummary.id} />
          </div>
        </section>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">Coverage analysis</h2>
            <p className="text-sm text-slate-600">Heatmap of rubric-weighted scores by tag and difficulty.</p>
          </div>
        </header>
        <div className="mt-4">
          <CoverageHeatmap matrix={coverageMatrix} />
        </div>
      </section>

      <section className="space-y-4">
        <header>
          <h2 className="text-xl font-semibold text-slate-900">Latest outputs & judgments</h2>
          <p className="text-sm text-slate-600">Inspect how prompts perform across datasets and judge scores.</p>
        </header>
        <RunOutputViewer outputs={outputs} />
      </section>

      <section className="space-y-4">
        <header>
          <h2 className="text-xl font-semibold text-slate-900">Human-in-the-loop review</h2>
          <p className="text-sm text-slate-600">Approve or reject automated prompt refinements before rollout.</p>
        </header>
        {suggestions && suggestions.length > 0 ? (
          <div className="space-y-6">
            {suggestions.map((suggestion) => (
              <ReviewSuggestionCard key={suggestion.id} suggestion={suggestion} />
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-500">
            No suggestions awaiting review.
          </div>
        )}
      </section>
    </div>
  );
}
