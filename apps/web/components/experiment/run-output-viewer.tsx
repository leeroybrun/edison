'use client';

interface JudgmentSummary {
  judgeConfigId: string;
  scores: Record<string, number>;
  rationales?: Record<string, string>;
}

interface OutputRecord {
  id: string;
  rawText: string;
  createdAt: string;
  modelRun: { modelConfig: { modelId: string; provider: string } };
  case: { id: string; input: Record<string, unknown>; tags: string[]; difficulty: number | null };
  judgments: JudgmentSummary[];
}

interface RunOutputViewerProps {
  outputs: OutputRecord[];
}

function formatJson(input: unknown) {
  try {
    return JSON.stringify(input, null, 2);
  } catch (error) {
    return String(input);
  }
}

export function RunOutputViewer({ outputs }: RunOutputViewerProps) {
  if (!outputs.length) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-500">
        No outputs captured yet.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {outputs.map((output) => (
        <article key={output.id} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h4 className="text-base font-semibold text-slate-900">Case {output.case.id}</h4>
              <p className="text-sm text-slate-600">
                {output.case.tags.join(', ') || 'untagged'} • Difficulty {output.case.difficulty ?? 'n/a'}
              </p>
            </div>
            <span className="rounded-lg bg-slate-900 px-3 py-1 text-sm font-medium text-white">
              {output.modelRun.modelConfig.provider} · {output.modelRun.modelConfig.modelId}
            </span>
          </header>

          <section className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="space-y-2 rounded-lg border border-slate-200 p-4">
              <h5 className="text-sm font-semibold text-slate-700">Input</h5>
              <pre className="max-h-64 overflow-auto rounded bg-slate-950/90 px-3 py-2 text-xs text-emerald-100">
                {formatJson(output.case.input)}
              </pre>
            </div>
            <div className="space-y-2 rounded-lg border border-slate-200 p-4">
              <h5 className="text-sm font-semibold text-slate-700">Model output</h5>
              <pre className="max-h-64 overflow-auto rounded bg-slate-50 px-3 py-2 text-sm text-slate-800">
                {output.rawText}
              </pre>
            </div>
          </section>

          <section className="mt-4 space-y-3">
            <h5 className="text-sm font-semibold text-slate-700">Judgments</h5>
            {output.judgments.length === 0 ? (
              <p className="text-sm text-slate-500">Awaiting evaluation.</p>
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {output.judgments.map((judgment) => (
                  <li key={judgment.judgeConfigId} className="rounded-lg border border-slate-200 p-4">
                    <h6 className="text-sm font-semibold text-slate-700">Judge {judgment.judgeConfigId}</h6>
                    <dl className="mt-2 space-y-1 text-xs text-slate-600">
                      {Object.entries(judgment.scores).map(([criterion, score]) => (
                        <div key={criterion} className="flex items-start justify-between gap-3">
                          <dt className="font-medium text-slate-700">{criterion}</dt>
                          <dd>{score.toFixed(2)}</dd>
                        </div>
                      ))}
                    </dl>
                    {judgment.rationales ? (
                      <div className="mt-3 rounded bg-slate-50 px-3 py-2 text-xs text-slate-600">
                        {Object.entries(judgment.rationales).map(([criterion, rationale]) => (
                          <p key={criterion}>
                            <span className="font-semibold text-slate-700">{criterion}:</span> {rationale}
                          </p>
                        ))}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </article>
      ))}
    </div>
  );
}
