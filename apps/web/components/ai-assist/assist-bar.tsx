'use client';

import { useState } from 'react';

interface AssistBarProps {
  label: string;
  onSelect: (value: string) => void;
  suggestions: string[];
}

export function AssistBar({ label, onSelect, suggestions }: AssistBarProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-600"
      >
        {label}
      </button>
      {open && (
        <div className="absolute z-10 mt-2 w-72 rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-lg">
          <ul className="space-y-2">
            {suggestions.map((suggestion) => (
              <li key={suggestion}>
                <button
                  type="button"
                  className="w-full rounded-md border border-transparent px-2 py-1 text-left hover:border-slate-200 hover:bg-slate-50"
                  onClick={() => {
                    onSelect(suggestion);
                    setOpen(false);
                  }}
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
