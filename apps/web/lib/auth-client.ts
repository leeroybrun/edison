'use client';

export function getAuthToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const match = document.cookie.match(/(?:^|; )edison_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function buildAuthHeaders(base?: HeadersInit): HeadersInit {
  const token = getAuthToken();
  const headers = new Headers(base ?? {});
  if (token) {
    headers.set('authorization', `Bearer ${token}`);
  }
  return headers;
}
