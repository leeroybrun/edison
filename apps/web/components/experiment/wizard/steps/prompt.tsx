'use client';

import type { FewShotExample } from '@edison/shared';
import { useState } from 'react';

import type { PromptDraft } from '../wizard';

interface PromptStepProps {
  defaultPrompt?: PromptDraft;
  onNext: (prompt: PromptDraft) => void | Promise<void>;
  onBack: () => void;
}

export function PromptStep({ defaultPrompt, onNext, onBack }: PromptStepProps) {
  const [name, setName] = useState(defaultPrompt?.name ?? 'Initial prompt');
  const [systemText, setSystemText] = useState(defaultPrompt?.systemText ?? '');
  const [text, setText] = useState(defaultPrompt?.text ?? '');
  const [fewShots, setFewShots] = useState<FewShotExample[]>(defaultPrompt?.fewShots ?? []);

  const updateExample = (index: number, patch: Partial<FewShotExample>) => {
    setFewShots((prev) => prev.map((example, idx) => (idx === index ? { ...example, ...patch } : example)));
  };

  const removeExample = (index: number) => {
    setFewShots((prev) => prev.filter((_, idx) => idx !== index));
  };

  const canContinue = text.trim().length > 10 && name.trim().length >= 3;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Craft the seed prompt</h3>
        <p className="text-sm text-slate-600">
          Provide the base instructions and optional system preface Edison will iterate on.
        </p>
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700" htmlFor="prompt-name">
          Prompt label
        </label>
        <input
          id="prompt-name"
          className="w-full rounded-lg border border-slate-200 p-3 text-sm"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700" htmlFor="system-text">
          System instructions (optional)
        </label>
        <textarea
          id="system-text"
          className="w-full rounded-lg border border-slate-200 p-3 text-sm"
          rows={4}
          placeholder="You are Edison, an elite prompt engineer..."
          value={systemText}
          onChange={(event) => setSystemText(event.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700" htmlFor="prompt-text">
          Prompt body
        </label>
        <textarea
          id="prompt-text"
          className="w-full rounded-lg border border-slate-200 p-3 text-sm"
          rows={8}
          placeholder="Outline the instructions, variables, and formatting requirements..."
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-800">Few-shot examples</h4>
            <p className="text-xs text-slate-500">Optional user/assistant pairs to anchor the behaviour.</p>
          </div>
          <button
            className="inline-flex items-center rounded-md border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            type="button"
            onClick={() => setFewShots((prev) => [...prev, { user: '', assistant: '' }])}
          >
            Add example
          </button>
        </div>
        {fewShots.length === 0 ? (
          <p className="text-xs text-slate-500">No examples added yet.</p>
        ) : (
          <div className="space-y-4">
            {fewShots.map((example, index) => (
              <div key={index} className="rounded-lg border border-slate-200 p-3">
                <div className="flex justify-between">
                  <p className="text-xs font-medium text-slate-600">Example {index + 1}</p>
                  <button
                    className="text-xs font-medium text-rose-600"
                    type="button"
                    onClick={() => removeExample(index)}
                  >
                    Remove
                  </button>
                </div>
                <div className="mt-3 space-y-2">
                  <textarea
                    className="w-full rounded border border-slate-200 p-2 text-xs"
                    rows={3}
                    placeholder="User message"
                    value={example.user}
                    onChange={(event) => updateExample(index, { user: event.target.value })}
                  />
                  <textarea
                    className="w-full rounded border border-slate-200 p-2 text-xs"
                    rows={3}
                    placeholder="Assistant response"
                    value={example.assistant}
                    onChange={(event) => updateExample(index, { assistant: event.target.value })}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

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
            await onNext({
              name,
              systemText: systemText.trim().length > 0 ? systemText : undefined,
              text,
              fewShots: fewShots.filter((example) => example.user.trim() && example.assistant.trim()),
            });
          }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
