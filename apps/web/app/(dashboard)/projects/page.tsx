import { cookies } from 'next/headers';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import { ExperimentWizard } from '@/components/experiment/wizard/wizard';

async function fetchMe(token: string) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';
  const response = await fetch(`${baseUrl}/trpc/auth.me`, {
    headers: {
      authorization: `Bearer ${token}`,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error('Failed to load user profile');
  }

  const payload = await response.json();
  return payload?.result?.data?.json ?? payload?.result?.data ?? null;
}

async function fetchExperiments(projectId: string, token: string) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';
  const query = new URLSearchParams({ input: JSON.stringify({ projectId }) });

  try {
    const response = await fetch(`${baseUrl}/trpc/experiment.listByProject?${query.toString()}`, {
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      console.error('Failed to fetch experiments', await response.text());
      return [];
    }

    const payload = await response.json();
    return payload?.result?.data?.json ?? [];
  } catch (error) {
    console.error('Failed to fetch experiments', error);
    return [];
  }
}

export default async function ProjectsPage() {
  const token = cookies().get('edison_token')?.value;
  if (!token) {
    redirect('/login');
  }

  let projectId: string | null = null;
  let projectName: string | null = null;
  try {
    const profile = await fetchMe(token);
    const project = profile?.projects?.[0];
    projectId = project?.id ?? null;
    projectName = project?.name ?? null;
  } catch (error) {
    console.error('Failed to load profile', error);
    redirect('/login');
  }

  if (!projectId) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold">No workspace yet</h2>
          <p className="text-sm text-slate-600">Create a project to begin experimenting with prompts.</p>
        </div>
      </div>
    );
  }

  const experiments = await fetchExperiments(projectId, token);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">{projectName ?? 'Workspace'}</h2>
        <p className="text-sm text-slate-600">Manage experiments and prompt iterations for this project.</p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Experiments</h3>
            <p className="text-sm text-slate-600">Create or inspect prompt iterations.</p>
          </div>
          <Link
            className="inline-flex items-center rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            href="#wizard"
          >
            New experiment
          </Link>
        </header>

        <ul className="mt-4 divide-y divide-slate-100">
          {experiments.length === 0 && (
            <li className="py-6 text-sm text-slate-500">No experiments yet. Create one to begin iterating.</li>
          )}
          {experiments.map((experiment) => (
            <li key={experiment.id} className="py-4">
              <h4 className="text-base font-semibold text-slate-900">{experiment.name}</h4>
              <p className="text-sm text-slate-600">{experiment.goal}</p>
            </li>
          ))}
        </ul>
      </section>

      <section id="wizard">
        <ExperimentWizard projectId={projectId} />
      </section>
    </div>
  );
}
