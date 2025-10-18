'use client';

import { diffLines, type Change } from 'diff';
import { useMemo } from 'react';

interface DiffViewerProps {
  original: string;
  revised: string;
}

function renderChange(change: Change, index: number) {
  const background = change.added
    ? 'bg-emerald-100 text-emerald-900'
    : change.removed
      ? 'bg-rose-100 text-rose-900'
      : 'bg-transparent text-slate-800';

  return (
    <pre
      key={`${index}-${change.added ? 'add' : change.removed ? 'del' : 'ctx'}`}
      className={`whitespace-pre-wrap rounded-md px-3 py-2 text-sm font-mono leading-6 ${background}`}
    >
      {change.value}
    </pre>
  );
}

export function DiffViewer({ original, revised }: DiffViewerProps) {
  const changes = useMemo(() => diffLines(original ?? '', revised ?? ''), [original, revised]);

  if (changes.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-500">
        No differences detected.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {changes.map((change, index) => renderChange(change, index))}
    </div>
  );
}
