import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-16">
      <section className="space-y-4">
        <p className="text-sm uppercase tracking-[0.2em] text-ink-muted">Prompt Operations Studio</p>
        <h1 className="text-5xl font-semibold tracking-tight text-ink">Edison</h1>
        <p className="max-w-2xl text-lg leading-relaxed text-ink-muted">
          Edison orchestrates multi-model evaluations, judge ensembles, and human-in-the-loop reviews so
          your prompts improve with every iteration.
        </p>
        <div className="flex gap-3">
          <Link
            className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:shadow-md"
            href="/experiments"
          >
            Launch experiment workspace
          </Link>
          <Link className="rounded-full border border-ink/10 px-4 py-2 text-sm font-medium" href="/about">
            Learn about Edison
          </Link>
        </div>
      </section>
      <section className="grid gap-6 rounded-3xl border border-ink/10 bg-white/50 p-8 shadow-xl shadow-ink/5">
        <h2 className="text-2xl font-semibold text-ink">Workflow snapshot</h2>
        <ol className="grid gap-4 text-ink-muted md:grid-cols-3">
          <li className="rounded-2xl border border-ink/10 p-4 shadow-sm">
            <h3 className="text-lg font-medium text-ink">Design</h3>
            <p className="text-sm leading-relaxed">
              Objectives, rubrics, prompt drafts, and datasets—crafted side-by-side with AI assist controls.
            </p>
          </li>
          <li className="rounded-2xl border border-ink/10 p-4 shadow-sm">
            <h3 className="text-lg font-medium text-ink">Experiment</h3>
            <p className="text-sm leading-relaxed">
              Execute multi-model runs with deterministic seeds, caching, and real-time telemetry.
            </p>
          </li>
          <li className="rounded-2xl border border-ink/10 p-4 shadow-sm">
            <h3 className="text-lg font-medium text-ink">Refine</h3>
            <p className="text-sm leading-relaxed">
              Judge ensembles surface weaknesses, refiner diffs propose edits, humans approve.
            </p>
          </li>
        </ol>
      </section>
    </main>
  );
}
