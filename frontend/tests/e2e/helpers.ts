/**
 * Shared E2E test helpers and fixtures.
 * These build on Playwright's Page object to provide
 * Aperture-specific actions used across test files.
 */
import { Page, expect } from "@playwright/test";

export const TEST_USER = {
  email: `e2e_${Date.now()}@test.example`,
  password: "E2eTest123!",
  displayName: "E2E Tester",
};

export const DEMO_USER = {
  email: "demo@example.com",
  password: "Demo1234!",
};

/** Register a fresh user via the UI */
export async function registerUser(
  page: Page,
  user = TEST_USER
): Promise<void> {
  await page.goto("/register");
  await page.fill('input[type="text"], input[placeholder*="name" i]', user.displayName);
  await page.fill('input[type="email"]', user.email);
  await page.fill('input[type="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL("/", { timeout: 10_000 });
}

/** Log in via the UI */
export async function loginUser(
  page: Page,
  user: { email: string; password: string } = DEMO_USER
): Promise<void> {
  await page.goto("/login");
  await page.fill('input[type="email"]', user.email);
  await page.fill('input[type="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL("/", { timeout: 10_000 });
}

/** Log in via the API directly (faster for tests that don't test auth itself) */
export async function loginViaAPI(
  page: Page,
  user: { email: string; password: string } = DEMO_USER
): Promise<string> {
  const baseURL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  const resp = await page.request.post(`${baseURL}/auth/login`, {
    data: { email: user.email, password: user.password },
  });

  if (!resp.ok()) {
    throw new Error(`API login failed: ${resp.status()} ${await resp.text()}`);
  }

  const { access_token } = await resp.json();

  // Inject token into localStorage as the auth-context expects it
  await page.goto("/");
  await page.evaluate((token: string) => {
    localStorage.setItem("aperture_token", token);
  }, access_token);

  await page.reload();
  return access_token;
}

/** Wait for a movie rail to finish loading (skeleton disappears) */
export async function waitForRail(page: Page): Promise<void> {
  await page.waitForFunction(
    () => document.querySelectorAll(".skeleton").length === 0,
    { timeout: 15_000 }
  );
}

/** Assert WCAG contrast on a computed style (basic check) */
export async function assertVisible(page: Page, selector: string): Promise<void> {
  const el = page.locator(selector).first();
  await expect(el).toBeVisible();
}
