import type { Rubric } from '@edison/shared';
import { NextResponse } from 'next/server';

import {
  authenticate,
  createExperiment,
  listDatasets,
  listExperiments,
  loginUser,
  registerUser,
  resetStore,
  getDefaultContext,
  createSessionForUser,
} from './state';

const ONE_WEEK = 60 * 60 * 24 * 7;

export function handleRegister(body: {
  email: string;
  password: string;
  name: string;
  workspaceName?: string;
}) {
  resetStore();
  const result = registerUser(body);
  const response = NextResponse.json({
    result: {
      data: {
        json: {
          token: result.token,
          user: {
            id: result.user.id,
            email: result.user.email,
            name: result.user.name,
          },
          project: result.project,
        },
      },
    },
  });

  response.cookies.set('edison_token', result.token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    maxAge: ONE_WEEK,
    path: '/',
  });

  return response;
}

export function handleLogin(body: { email: string; password: string }) {
  try {
    const result = loginUser(body);
    const response = NextResponse.json({
      result: {
        data: {
          json: {
            token: result.token,
            user: {
              id: result.user.id,
              email: result.user.email,
              name: result.user.name,
            },
            projects: result.projects,
          },
        },
      },
    });

    response.cookies.set('edison_token', result.token, {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      maxAge: ONE_WEEK,
      path: '/',
    });

    return response;
  } catch (error) {
    const fallback = getDefaultContext();
    if (!fallback || fallback.user.email !== body.email) {
      throw error;
    }

    const token = createSessionForUser(fallback.user.id);
    const response = NextResponse.json({
      result: {
        data: {
          json: {
            token,
            user: {
              id: fallback.user.id,
              email: fallback.user.email,
              name: fallback.user.name,
            },
            projects: [fallback.project],
          },
        },
      },
    });

    response.cookies.set('edison_token', token, {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      maxAge: ONE_WEEK,
      path: '/',
    });

    return response;
  }
}

export async function handleTrpc(request: Request, segments: string[]): Promise<Response> {
  const route = Array.isArray(segments) ? segments.join('.') : `${segments ?? ''}`;
  const method = request.method.toUpperCase();

  try {
    if (route === 'auth.me') {
      try {
        const token = extractToken(request.headers.get('authorization'), request.headers.get('cookie'));
        const { user, project } = authenticate(token);
        return buildTrpcJson({
          id: user.id,
          email: user.email,
          name: user.name,
          projects: [project],
        });
      } catch (error) {
        const fallback = getDefaultContext();
        if (!fallback) {
          return buildTrpcJson(null);
        }
        return buildTrpcJson({
          id: fallback.user.id,
          email: fallback.user.email,
          name: fallback.user.name,
          projects: [fallback.project],
        });
      }
    }

    if (route === 'dataset.list' && method === 'POST') {
      const token = extractToken(request.headers.get('authorization'), request.headers.get('cookie'));
      const { project } = authenticate(token);
      const body = await request.json();
      const input = (body?.json ?? {}) as { projectId?: string };
      const projectId = input.projectId ?? project.id;
      const datasets = listDatasets(projectId).map((dataset) => ({
        id: dataset.id,
        name: dataset.name,
        kind: dataset.kind,
        description: dataset.description,
        cases: dataset.cases,
      }));
      return NextResponse.json({ result: { data: datasets } });
    }

    if (route === 'experiment.listByProject') {
      const url = new URL(request.url);
      const token = extractToken(request.headers.get('authorization'), request.headers.get('cookie'));
      const { project } = authenticate(token);
      const inputRaw = url.searchParams.get('input');
      const parsed = inputRaw ? (JSON.parse(inputRaw) as { projectId?: string }) : {};
      const projectId = parsed.projectId ?? project.id;
      const experiments = listExperiments(projectId).map((experiment) => ({
        id: experiment.id,
        name: experiment.name,
        goal: experiment.goal,
      }));
      return buildTrpcJson(experiments);
    }

    if (route === 'experiment.create' && method === 'POST') {
      const token = extractToken(request.headers.get('authorization'), request.headers.get('cookie'));
      const { project } = authenticate(token);
      const body = await request.json();
      const input = (body?.json ?? {}) as {
        projectId: string;
        name: string;
        goal: string;
        rubric: Rubric;
      };
      const projectId = input.projectId ?? project.id;
      createExperiment(projectId, {
        name: input.name,
        goal: input.goal,
        rubric: input.rubric,
      });
      return NextResponse.json({ result: { data: { json: { ok: true } } } });
    }

    return NextResponse.json({ error: { message: `Unhandled route ${route}` } }, { status: 404 });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json({ error: { message } }, { status: 400 });
  }
}

function extractToken(header: string | null, cookieHeader?: string | null): string {
  if (header) {
    const match = header.match(/Bearer\s+(.*)$/i);
    if (match) {
      return match[1];
    }
  }

  if (cookieHeader) {
    const cookieMatch = cookieHeader.match(/(?:^|;\s*)edison_token=([^;]+)/);
    if (cookieMatch) {
      return decodeURIComponent(cookieMatch[1]);
    }
  }

  throw new Error('Unauthorized');
}

function buildTrpcJson(payload: unknown): Response {
  return NextResponse.json({ result: { data: { json: payload } } });
}
