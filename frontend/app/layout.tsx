import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Edison — Prompt Experimentation",
  description: "Design, test, and refine prompts with AI assistance."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-ink antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
