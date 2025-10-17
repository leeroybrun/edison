export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f8fafc]">
      <div className="border-b border-ink/10 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="text-lg font-semibold tracking-tight text-ink">Edison Lab</div>
          <nav className="flex items-center gap-4 text-sm text-ink-muted">
            <a className="hover:text-ink" href="/experiments">
              Experiments
            </a>
            <a className="hover:text-ink" href="/providers">
              Providers
            </a>
            <a className="hover:text-ink" href="/settings">
              Settings
            </a>
          </nav>
        </div>
      </div>
      {children}
    </div>
  );
}
