import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

import { Prisma, PrismaClient, JudgeMode, LLMProvider, UserRole } from '@prisma/client';
import { config } from 'dotenv';
import { hashPassword } from '../packages/api/src/lib/auth';

const currentDir = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(currentDir, '../.env') });

if (!process.env.DATABASE_URL) {
  const user = process.env.POSTGRES_USER ?? 'edison';
  const password = process.env.POSTGRES_PASSWORD ?? 'password';
  const host = process.env.POSTGRES_HOST ?? 'localhost';
  const port = process.env.POSTGRES_PORT ?? '5432';
  const database = process.env.POSTGRES_DB ?? 'edison';
  process.env.DATABASE_URL = `postgresql://${user}:${password}@${host}:${port}/${database}`;
}

const prisma = new PrismaClient();

async function upsertUser() {
  const email = process.env.SEED_ADMIN_EMAIL ?? 'admin@edison.local';
  const password = process.env.SEED_ADMIN_PASSWORD ?? 'ChangeMeNow123!';
  const name = process.env.SEED_ADMIN_NAME ?? 'Edison Admin';

  const passwordHash = await hashPassword(password);

  const user = await prisma.user.upsert({
    where: { email },
    update: { name, passwordHash, role: UserRole.OWNER },
    create: {
      email,
      name,
      passwordHash,
      role: UserRole.OWNER,
    },
  });

  return { user, plainPassword: password };
}

async function upsertProject(ownerId: string) {
  const projectName = process.env.SEED_PROJECT_NAME ?? 'Demo Workbench';
  const slug = process.env.SEED_PROJECT_SLUG ?? 'demo-workbench';

  const project = await prisma.project.upsert({
    where: { slug },
    update: {
      name: projectName,
      description: 'Sample project seeded for Edison development environment.',
    },
    create: {
      slug,
      name: projectName,
      description: 'Sample project seeded for Edison development environment.',
      members: {
        create: {
          userId: ownerId,
          role: UserRole.OWNER,
        },
      },
    },
    include: { members: true },
  });

  const existingMembership = project.members.find((member) => member.userId === ownerId);
  if (!existingMembership) {
    await prisma.projectMember.create({
      data: { projectId: project.id, userId: ownerId, role: UserRole.OWNER },
    });
  }

  return project;
}

async function upsertDataset(projectId: string) {
  const datasetName = 'Customer Support Scenarios';
  const existing = await prisma.dataset.findFirst({ where: { projectId, name: datasetName } });

  if (existing) {
    await prisma.case.deleteMany({ where: { datasetId: existing.id } });
    return prisma.dataset.update({
      where: { id: existing.id },
      data: {
        description: 'A small set of customer email examples for experimentation.',
        metadata: {
          seeded: true,
          updatedAt: new Date().toISOString(),
        },
        cases: {
          create: seedCases(),
        },
      },
    });
  }

  return prisma.dataset.create({
    data: {
      projectId,
      name: datasetName,
      kind: 'GOLDEN',
      description: 'A small set of customer email examples for experimentation.',
      metadata: {
        seeded: true,
        createdAt: new Date().toISOString(),
      },
      cases: {
        create: seedCases(),
      },
    },
  });
}

function seedCases() {
  return [
    {
      input: {
        subject: 'Subscription Cancellation',
        customer_message:
          "Hi, I'd like to cancel my Edison subscription effective immediately. I'm not using the product anymore.",
        history: [],
      },
      expected: {
        strategy: 'Confirm cancellation, acknowledge reason, offer optional feedback link.',
      },
      tags: ['cancellation', 'support'],
      difficulty: 2,
      metadata: { seeded: true },
    },
    {
      input: {
        subject: 'Billing Issue',
        customer_message:
          'My invoice shows a higher amount than expected. Can you explain the additional charges for October?',
        history: [
          { role: 'agent', message: 'Happy to help! Can you share your account email?' },
          { role: 'customer', message: 'yes, support-demo@acme.test' },
        ],
      },
      expected: {
        strategy: 'Break down invoice, apologise for confusion, provide clear next steps.',
      },
      tags: ['billing', 'support'],
      difficulty: 3,
      metadata: { seeded: true },
    },
  ];
}

function normalizeMetadata(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

async function upsertExperiment(projectId: string, datasetId: string, ownerId: string) {
  const name = 'Prompt Quality Benchmark';
  const existing = await prisma.experiment.findFirst({
    where: { projectId, name },
    include: {
      promptVersions: { orderBy: { version: 'desc' }, take: 1 },
    },
  });

  const basePrompt = {
    name: 'Support Agent v1',
    systemText:
      'You are Edison, an empathetic customer support assistant. Always provide concise, actionable replies.',
    text: `You are responding to the following customer email:

{{customer_message}}

Respond as a helpful support agent. Include:
1. Clear acknowledgement.
2. Concise resolution steps.
3. Optional follow-up question if clarification is needed.`,
    fewShots: [
      {
        user: 'My device will not turn on after the latest update. Help!',
        assistant:
          "I'm sorry your device isn't turning on. Let's try a quick reset together... (sample response truncated).",
      },
    ],
  };

  if (existing) {
    await prisma.modelConfig.deleteMany({ where: { experimentId: existing.id } });
    await prisma.judgeConfig.deleteMany({ where: { experimentId: existing.id } });

    const latestPrompt = existing.promptVersions[0];
    if (latestPrompt) {
      await prisma.promptVersion.update({
        where: { id: latestPrompt.id },
        data: {
          text: basePrompt.text,
          systemText: basePrompt.systemText,
          fewShots: basePrompt.fewShots,
          metadata: { ...normalizeMetadata(latestPrompt.metadata), name: basePrompt.name, seeded: true },
        },
      });
    }

    return prisma.experiment.update({
      where: { id: existing.id },
      data: {
        description: 'Baseline prompt benchmark seeded for local development.',
        goal: 'Maintain consistent high-quality customer support responses across scenarios.',
        rubric: {
          dimensions: [
            { id: 'clarity', label: 'Clarity', weight: 0.4, description: 'Response is clear and easy to follow.' },
            { id: 'empathy', label: 'Empathy', weight: 0.3, description: 'Tone is empathetic and human.' },
            { id: 'actionability', label: 'Actionability', weight: 0.3, description: 'Provides concrete next steps.' },
          ],
        },
        stopRules: {
          maxIterations: 5,
          maxBudgetUsd: 25,
          convergenceWindow: 3,
          minDeltaThreshold: 0.01,
        },
        selectorConfig: { datasetIds: [datasetId] },
        modelConfigs: {
          create: [
            {
              provider: LLMProvider.OPENAI,
              modelId: 'gpt-4o-mini',
              params: { temperature: 0.3, maxTokens: 512 },
              isActive: true,
            },
          ],
        },
        judgeConfigs: {
          create: [
            {
              provider: LLMProvider.OPENAI,
              modelId: 'gpt-4o-mini',
              mode: JudgeMode.POINTWISE,
              systemPrompt:
                'Score the candidate response from 1-5 for clarity, empathy, and actionability. Return a JSON object.',
            },
          ],
        },
      },
    });
  }

  return prisma.experiment.create({
    data: {
      projectId,
      name,
      description: 'Baseline prompt benchmark seeded for local development.',
      goal: 'Maintain consistent high-quality customer support responses across scenarios.',
      rubric: {
        dimensions: [
          { id: 'clarity', label: 'Clarity', weight: 0.4, description: 'Response is clear and easy to follow.' },
          { id: 'empathy', label: 'Empathy', weight: 0.3, description: 'Tone is empathetic and human.' },
          { id: 'actionability', label: 'Actionability', weight: 0.3, description: 'Provides concrete next steps.' },
        ],
      },
      safetyConfig: { enabled: true, flags: ['toxicity', 'pii'] },
      selectorConfig: { datasetIds: [datasetId] },
      refinerConfig: { maxSuggestions: 3, strategy: 'differential' },
      stopRules: {
        maxIterations: 5,
        maxBudgetUsd: 25,
        convergenceWindow: 3,
        minDeltaThreshold: 0.01,
      },
      promptVersions: {
        create: {
          version: 1,
          text: basePrompt.text,
          systemText: basePrompt.systemText,
          fewShots: basePrompt.fewShots,
          metadata: { name: basePrompt.name, seeded: true },
          createdBy: ownerId,
        },
      },
      modelConfigs: {
        create: [
          {
            provider: LLMProvider.OPENAI,
            modelId: 'gpt-4o-mini',
            params: { temperature: 0.3, maxTokens: 512 },
            isActive: true,
          },
        ],
      },
      judgeConfigs: {
        create: [
          {
            provider: LLMProvider.OPENAI,
            modelId: 'gpt-4o-mini',
            mode: JudgeMode.POINTWISE,
            systemPrompt:
              'Score the candidate response from 1-5 for clarity, empathy, and actionability. Return a JSON object.',
          },
        ],
      },
    },
  });
}

async function main() {
  console.log('🌱 Seeding Edison development data...');

  await prisma.$queryRawUnsafe('SELECT 1').catch((error) => {
    if (error instanceof Prisma.PrismaClientInitializationError) {
      console.error('❌ Unable to connect to PostgreSQL using DATABASE_URL:', process.env.DATABASE_URL);
      console.error('   Make sure Postgres is running and credentials in .env are correct.');
    }
    throw error;
  });

  const { user, plainPassword } = await upsertUser();
  const project = await upsertProject(user.id);
  const dataset = await upsertDataset(project.id);
  const experiment = await upsertExperiment(project.id, dataset.id, user.id);

  console.log('✅ Seed complete');
  console.log(`   Admin Email: ${user.email}`);
  console.log(`   Admin Password: ${plainPassword}`);
  console.log(`   Project: ${project.name} (${project.slug})`);
  console.log(`   Dataset: ${dataset.name}`);
  console.log(`   Experiment: ${experiment.name}`);
}

main()
  .catch((error) => {
    if (error instanceof Prisma.PrismaClientInitializationError) {
      console.error('❌ Seed failed: database connection error.');
    } else if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2021') {
      console.error('❌ Seed failed: database schema not found. Run `DATABASE_URL=... pnpm --filter @edison/api prisma migrate deploy` first.');
    } else {
      console.error('❌ Seed failed', error);
    }
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
