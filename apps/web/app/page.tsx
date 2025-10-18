import Link from 'next/link';

const quickStart = [
  'Create an experiment with a clear objective and rubric.',
  'Add datasets that capture the scenarios you care about.',
  'Run multi-model evaluations and review AI judge feedback.',
  'Approve targeted refinements to evolve your prompt safely.',
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Getting started</h2>
        <p className="mt-2 text-sm text-slate-600">
          Edison coordinates LLM execution, evaluation, and refinement so you can focus on intent.
        </p>
        <ol className="mt-4 list-decimal space-y-2 pl-6 text-sm text-slate-700">
          {quickStart.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold">Projects</h2>
        <p className="mt-2 text-sm text-slate-600">
          Organize experiments by project to manage credentials, datasets, and access control.
        </p>
        <Link
          className="mt-4 inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
          href="/(dashboard)/projects"
        >
          View projects
        </Link>
      </section>
    </div>
  );
}
