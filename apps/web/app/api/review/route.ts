import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';

export async function POST(request: Request) {
  const token = cookies().get('edison_token')?.value;
  if (!token) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
  }

  const body = await request.json();

  const payload = { id: 0, json: body };

  const response = await fetch(`${API_BASE_URL}/trpc/review.reviewSuggestion`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json().catch(() => ({}));

  if (!response.ok || result.error) {
    return NextResponse.json({ error: result.error?.message ?? 'Review failed' }, { status: response.status || 500 });
  }

  return NextResponse.json(result.result?.data?.json ?? result.result?.data ?? { ok: true });
}
