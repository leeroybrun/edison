import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

interface Experiment {
  id: number;
  name: string;
  description?: string | null;
  status: string;
}

function useExperiments() {
  return useQuery<Experiment[]>({
    queryKey: ["experiments"],
    queryFn: async () => {
      const response = await apiClient.get<Experiment[]>("/experiments");
      return response.data;
    }
  });
}

export default function ExperimentsPage() {
  const { data, isLoading } = useExperiments();

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-12">
      <header className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-ink-muted">Experiments</p>
          <h1 className="text-3xl font-semibold text-ink">Iteration history</h1>
        </div>
        <Button intent="outline">New experiment</Button>
      </header>
      <section className="rounded-3xl border border-ink/10 bg-white p-6 shadow-md">
        <h2 className="text-xl font-semibold text-ink">Recent experiments</h2>
        {isLoading ? (
          <p className="mt-4 text-sm text-ink-muted">Loading experiments…</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {(data ?? []).map((experiment) => (
              <li key={experiment.id} className="flex items-center justify-between rounded-2xl border border-ink/10 p-4">
                <div>
                  <p className="text-base font-medium text-ink">{experiment.name}</p>
                  {experiment.description ? (
                    <p className="text-sm text-ink-muted">{experiment.description}</p>
                  ) : null}
                </div>
                <span className="rounded-full bg-ink/5 px-3 py-1 text-xs uppercase tracking-wide text-ink-muted">
                  {experiment.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
