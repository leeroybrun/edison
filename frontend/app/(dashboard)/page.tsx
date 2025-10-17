import Link from "next/link";

const steps = [
  {
    title: "Objective",
    description: "Describe the experiment outcome and guardrails.",
    action: "Draft"
  },
  {
    title: "Rubric",
    description: "Define criteria and weights to evaluate answers.",
    action: "Auto-build"
  },
  {
    title: "Prompt",
    description: "Craft and iterate on instructions with AI assist.",
    action: "Open editor"
  },
  {
    title: "Datasets",
    description: "Upload golden cases or synthesize coverage.",
    action: "Manage cases"
  },
  {
    title: "Models",
    description: "Choose target LLMs and parameter sweeps.",
    action: "Configure"
  }
];

export default function DashboardPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-12">
      <header className="flex items-center justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-ink-muted">Experiment control</p>
          <h1 className="text-4xl font-semibold text-ink">New experiment</h1>
        </div>
        <Link
          className="rounded-full border border-ink/10 px-4 py-2 text-sm font-medium text-ink shadow-sm hover:border-accent hover:text-accent"
          href="/experiments/new"
        >
          Wizard mode
        </Link>
      </header>
      <section className="grid gap-4 md:grid-cols-2">
        {steps.map((step) => (
          <article key={step.title} className="rounded-3xl border border-ink/10 bg-white p-6 shadow-md">
            <h2 className="text-xl font-semibold text-ink">{step.title}</h2>
            <p className="mt-2 text-sm text-ink-muted">{step.description}</p>
            <button className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-accent">
              {step.action}
              <span aria-hidden>→</span>
            </button>
          </article>
        ))}
      </section>
    </main>
  );
}
