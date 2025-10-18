import { expect, test } from '@playwright/test';

const LONG_PROMPT = `You are a customer support assistant. When given a question, provide a concise, empathetic response that references relevant policies and offers next steps.`;

const JUDGE_PROMPT = `You are an impartial evaluator. Score responses against the rubric and provide one-sentence rationales per criterion.`;

test.describe('Experiment wizard', () => {
  test('guides a new user through experiment creation', async ({ page }) => {
    await page.goto('/register');

    await page.fill('input[name="name"]', 'Playwright Tester');
    await page.fill('input[name="workspaceName"]', 'QA Workspace');
    await page.fill('input[name="email"]', 'tester@example.com');
    await page.fill('input[name="password"]', 'StrongPassword!1');
    await page.getByRole('button', { name: 'Create account' }).click();
    await page.waitForResponse((response) => response.url().includes('/api/auth/register') && response.ok());

    await page.goto('/login');
    await page.getByLabel('Email').fill('tester@example.com');
    await page.getByLabel('Password').fill('StrongPassword!1');
    const loginResponsePromise = page.waitForResponse((response) => response.url().includes('/api/auth/login'));
    await page.getByRole('button', { name: 'Sign in' }).click();
    const loginResponse = await loginResponsePromise;
    expect.soft(loginResponse.ok()).toBeTruthy();

    await expect(page).toHaveURL(/\/projects$/, { timeout: 15000 });
    await expect(page.getByRole('heading', { name: /workspace/i })).toBeVisible();

    await page.getByRole('link', { name: /new experiment/i }).click();

    await page.fill('#experiment-name', 'Playwright Experiment');
    await page.fill('textarea', 'Improve responses to complex billing issues while maintaining empathy and policy adherence.');
    await page.getByRole('button', { name: 'Continue' }).click();

    await expect(page.getByRole('heading', { name: /evaluation rubric/i })).toBeVisible();
    await page.getByRole('button', { name: 'Continue' }).click();

    await expect(page.getByRole('heading', { name: /seed prompt/i })).toBeVisible();
    await page.fill('#prompt-text', LONG_PROMPT);
    await page.getByRole('button', { name: 'Continue' }).click();

    await expect(page.getByRole('heading', { name: /select datasets/i })).toBeVisible();
    await page.waitForSelector('button:has-text("Continue"):not([disabled])');
    await page.getByRole('button', { name: 'Continue' }).click();

    await expect(page.getByRole('heading', { name: /execution models/i })).toBeVisible();
    await page.fill('input[placeholder="gpt-4o"]', 'gpt-4o');
    await page.getByRole('button', { name: 'Continue' }).click();

    await expect(page.getByRole('heading', { name: /configure judges/i })).toBeVisible();
    await page.fill('textarea[placeholder*="expert evaluator"]', JUDGE_PROMPT);
    await page.getByRole('button', { name: 'Continue' }).click();

    await expect(page.getByRole('heading', { name: /control iteration cost/i })).toBeVisible();
    await page.fill('input[type="number"]', '5');
    await page.getByRole('button', { name: 'Finish setup' }).click();

    await expect(page.getByText(/Experiment drafted./i)).toBeVisible();
  });
});
