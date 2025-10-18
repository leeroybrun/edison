import { handleTrpc } from '../../e2e-backend/handlers';

const API_BASE_URL = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080';

type Params = { params: { trpc: string[] } };

async function proxy(request: Request, { params }: Params) {
  const segments = params.trpc ?? [];
  if (process.env.E2E_MODE === 'true') {
    return handleTrpc(request, segments);
  }

  const url = new URL(request.url);
  const targetPath = segments.join('/');
  const targetUrl = `${API_BASE_URL}/trpc/${targetPath}${url.search}`;
  const init: RequestInit = {
    method: request.method,
    headers: new Headers(request.headers),
    redirect: 'follow',
  };

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.text();
  }

  const response = await fetch(targetUrl, init);
  const headers = new Headers(response.headers);
  headers.delete('content-length');

  const body = response.body ?? (await response.blob());
  return new Response(body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export { proxy as GET, proxy as POST };
