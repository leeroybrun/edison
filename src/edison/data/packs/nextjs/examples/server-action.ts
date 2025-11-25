'use server';

export async function createItem(input: { name: string }) {
  if (!input.name?.trim()) throw new Error('Name required');
  return { id: 'it_1', ...input };
}

