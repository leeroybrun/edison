import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { handleLogin } from '../../e2e-backend/handlers';

const API_BASE_URL = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';

export async function POST(request: Request) {
  const body = await request.json();

  if (process.env.E2E_MODE === 'true') {
    return handleLogin(body);
  }

  const payload = { id: 0, json: body };

  const response = await fetch(`${API_BASE_URL}/trpc/auth.login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok || data.error) {
    return NextResponse.json(
      { error: data.error?.message ?? 'Invalid credentials' },
      { status: response.status || 401 },
    );
  }

  const result = data.result?.data?.json ?? data.result?.data;
  if (!result?.token) {
    return NextResponse.json({ error: 'Malformed response from API' }, { status: 500 });
  }

  const cookieStore = cookies();
  cookieStore.set('edison_token', result.token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 60 * 60 * 24 * 7,
    path: '/',
  });

  return NextResponse.json({
    user: result.user,
    projects: result.projects,
  });
}
