import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Edison Prompt Workbench',
  description: 'Iterate on prompts with AI and human feedback.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-100 text-slate-900 min-h-screen">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <header className="mb-8">
            <h1 className="text-3xl font-semibold tracking-tight">Edison Prompt Workbench</h1>
            <p className="text-sm text-slate-600">Design. Evaluate. Refine.</p>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
