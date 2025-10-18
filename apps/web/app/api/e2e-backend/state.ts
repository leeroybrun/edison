import { createHash, randomUUID } from 'crypto';

import type { Rubric } from '@edison/shared';

export type E2EUser = {
  id: string;
  email: string;
  passwordHash: string;
  name: string;
  projectId: string;
};

export type E2EProject = {
  id: string;
  name: string;
  slug: string;
};

export type E2EDataset = {
  id: string;
  projectId: string;
  name: string;
  kind: 'SYNTHETIC' | 'GOLDEN' | 'ADVERSARIAL';
  description?: string;
  cases: Array<{ id: string }>;
};

export type E2EExperiment = {
  id: string;
  projectId: string;
  name: string;
  goal: string;
  rubric: Rubric;
};

type SessionState = {
  token: string;
  userId: string;
};

type Store = {
  users: Map<string, E2EUser>;
  emails: Map<string, string>;
  sessions: Map<string, SessionState>;
  projects: Map<string, E2EProject>;
  datasets: Map<string, E2EDataset[]>;
  experiments: Map<string, E2EExperiment[]>;
};

declare global {
  // eslint-disable-next-line no-var
  var __edisonE2EStore: Store | undefined;
}

function createEmptyStore(): Store {
  return {
    users: new Map(),
    emails: new Map(),
    sessions: new Map(),
    projects: new Map(),
    datasets: new Map(),
    experiments: new Map(),
  };
}

function getStore(): Store {
  if (!globalThis.__edisonE2EStore) {
    globalThis.__edisonE2EStore = createEmptyStore();
  }
  return globalThis.__edisonE2EStore;
}

export function resetStore(): void {
  globalThis.__edisonE2EStore = createEmptyStore();
}

export function registerUser(payload: { email: string; password: string; name: string; workspaceName?: string }) {
  const store = getStore();
  const existing = store.emails.get(payload.email);
  if (existing) {
    throw new Error('User already exists');
  }

  const userId = randomUUID();
  const projectId = randomUUID();
  const projectName = payload.workspaceName?.trim() || `${payload.name.split(' ')[0]}'s Workspace`;
  const project: E2EProject = {
    id: projectId,
    name: projectName,
    slug: slugify(projectName),
  };

  const user: E2EUser = {
    id: userId,
    email: payload.email,
    name: payload.name,
    passwordHash: hashPassword(payload.password),
    projectId,
  };

  store.users.set(userId, user);
  store.emails.set(payload.email, userId);
  store.projects.set(projectId, project);
  store.datasets.set(projectId, [createDefaultDataset(projectId)]);
  store.experiments.set(projectId, []);

  const token = issueToken(userId);

  return { token, user, project };
}

export function loginUser(payload: { email: string; password: string }) {
  const store = getStore();
  const userId = store.emails.get(payload.email);
  if (!userId) {
    throw new Error('Invalid credentials');
  }
  const user = store.users.get(userId);
  if (!user) {
    throw new Error('Invalid credentials');
  }
  if (user.passwordHash !== hashPassword(payload.password)) {
    throw new Error('Invalid credentials');
  }

  const token = issueToken(userId);
  const project = store.projects.get(user.projectId)!;

  return {
    token,
    user,
    projects: [project],
  };
}

export function authenticate(token: string): { user: E2EUser; project: E2EProject } {
  const store = getStore();
  const session = store.sessions.get(token);
  if (!session) {
    throw new Error('Unauthorized');
  }
  const user = store.users.get(session.userId);
  if (!user) {
    throw new Error('Unauthorized');
  }
  const project = store.projects.get(user.projectId);
  if (!project) {
    throw new Error('Unauthorized');
  }
  return { user, project };
}

export function listDatasets(projectId: string): E2EDataset[] {
  const store = getStore();
  return store.datasets.get(projectId) ?? [];
}

export function listExperiments(projectId: string): E2EExperiment[] {
  const store = getStore();
  return store.experiments.get(projectId) ?? [];
}

export function createExperiment(projectId: string, input: {
  name: string;
  goal: string;
  rubric: Rubric;
}): E2EExperiment {
  const store = getStore();
  const experiment: E2EExperiment = {
    id: randomUUID(),
    projectId,
    name: input.name,
    goal: input.goal,
    rubric: input.rubric,
  };
  const experiments = store.experiments.get(projectId) ?? [];
  experiments.push(experiment);
  store.experiments.set(projectId, experiments);
  return experiment;
}

export function getDefaultContext(): { user: E2EUser; project: E2EProject } | null {
  const store = getStore();
  const firstUser = store.users.values().next().value as E2EUser | undefined;
  if (!firstUser) {
    return null;
  }
  const project = store.projects.get(firstUser.projectId);
  if (!project) {
    return null;
  }
  return { user: firstUser, project };
}

export function createSessionForUser(userId: string): string {
  return issueToken(userId);
}

function hashPassword(password: string): string {
  return createHash('sha256').update(password).digest('hex');
}

function issueToken(userId: string): string {
  const store = getStore();
  const token = randomUUID();
  store.sessions.set(token, { token, userId });
  return token;
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 32) || `workspace-${randomUUID().slice(0, 8)}`;
}

function createDefaultDataset(projectId: string): E2EDataset {
  const cases = Array.from({ length: 5 }, (_, index) => ({ id: `${projectId}-case-${index + 1}` }));
  return {
    id: randomUUID(),
    projectId,
    name: 'Starter set',
    kind: 'SYNTHETIC',
    description: 'Pre-seeded dataset for e2e flows',
    cases,
  };
}
