import type { Metadata } from 'next';

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: 'Sample Page',
    description: 'Demonstrates Next.js metadata API',
  };
}

