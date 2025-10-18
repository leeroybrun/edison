'use client';

import { useMemo, useState, useTransition } from 'react';

import { DiffViewer } from './diff-viewer';

interface ReviewSuggestionCardProps {
  suggestion: {
    id: string;
    note: string | null;
    diffUnified: string;
    targetCriteria: string[];
    createdAt: string;
    promptVersion: { id: string; version: number; text: string };
  };
}

async function submitReview(
  payload: { suggestionId: string; decision: 'APPROVE' | 'REJECT'; notes?: string },
) {
  const response = await fetch('/api/review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error?.error ?? 'Unable to submit review');
  }
}

export function ReviewSuggestionCard({ suggestion }: ReviewSuggestionCardProps) {
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const revisedPrompt = useMemo(() => {
    try {
      const payload = { id: suggestion.id, diff: suggestion.diffUnified };
      return payload.diff
        .split('\n')
        .map((line) => {
          if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) {
            return '';
          }
          if (line.startsWith('+')) {
            return line.slice(1);
          }
          if (line.startsWith('-')) {
            return '';
          }
          return line;
        })
        .join('\n');
    } catch (err) {
      return suggestion.promptVersion.text;
    }
  }, [suggestion.diffUnified, suggestion.id, suggestion.promptVersion.text]);

  const handleDecision = (decision: 'APPROVE' | 'REJECT') => {
    setError(null);
    setSuccess(null);
    startTransition(async () => {
      try {
        await submitReview({ suggestionId: suggestion.id, decision, notes: notes.trim() || undefined });
        setSuccess(decision === 'APPROVE' ? 'Suggestion approved.' : 'Suggestion rejected.');
        setNotes('');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Review failed');
      }
    });
  };

  return (
    <article className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h4 className="text-base font-semibold text-slate-900">Suggestion #{suggestion.promptVersion.version}</h4>
          <p className="text-sm text-slate-600">Targets: {suggestion.targetCriteria.join(', ') || 'General improvements'}</p>
        </div>
        <time className="text-sm text-slate-500" dateTime={suggestion.createdAt}>
          {new Date(suggestion.createdAt).toLocaleString()}
        </time>
      </header>

      <DiffViewer original={suggestion.promptVersion.text} revised={revisedPrompt} />

      {suggestion.note ? (
        <p className="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-700">{suggestion.note}</p>
      ) : null}

      <label className="block text-sm font-medium text-slate-700">
        Reviewer notes
        <textarea
          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500"
          placeholder="Document rationale or outstanding concerns"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </label>

      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      {success ? <p className="text-sm text-emerald-600">{success}</p> : null}

      <footer className="flex flex-wrap gap-3">
        <button
          className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
          disabled={isPending}
          onClick={() => handleDecision('APPROVE')}
          type="button"
        >
          Approve suggestion
        </button>
        <button
          className="inline-flex items-center justify-center rounded-lg border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-50 disabled:opacity-50"
          disabled={isPending}
          onClick={() => handleDecision('REJECT')}
          type="button"
        >
          Reject suggestion
        </button>
      </footer>
    </article>
  );
}
