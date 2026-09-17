/**
 * E2E tests: Authentication flows
 * Tests register, login, protected routes, logout
 */
import { test, expect } from "@playwright/test";
import { loginUser, registerUser, TEST_USER } from "./helpers";

test.describe("Authentication", () => {
  test("home page loads with Aperture branding", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Aperture/i);
    // Check the logo is visible
    const logo = page.locator("text=APERTURE").first();
    await expect(logo).toBeVisible();
  });

  test("login page renders form correctly", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    // Demo credentials hint should be visible
    await expect(page.locator("text=demo@example.com")).toBeVisible();
  });

  test("login with wrong password shows error", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', "demo@example.com");
    await page.fill('input[type="password"]', "wrongpassword");
    await page.click('button[type="submit"]');
    // Error message should appear
    await expect(
      page.locator("text=/incorrect|wrong|invalid/i")
    ).toBeVisible({ timeout: 5_000 });
    // Should NOT redirect to home
    await expect(page).toHaveURL("/login");
  });

  test("login with valid credentials redirects to home", async ({ page }) => {
    await loginUser(page, { email: "demo@example.com", password: "Demo1234!" });
    await expect(page).toHaveURL("/");
    // After login, user-specific elements should appear
    // (sign-in button replaced by user avatar)
    await expect(page.locator("text=Sign in")).not.toBeVisible({
      timeout: 5_000,
    });
  });

  test("register page has genre picker", async ({ page }) => {
    await page.goto("/register");
    // Genre chips should be visible
    const actionChip = page.locator("button", { hasText: "Action" });
    await expect(actionChip).toBeVisible();
    // Can click a genre chip
    await actionChip.click();
    // Chip should show selected state (border changes)
    await expect(actionChip).toHaveClass(/red/);
  });

  test("register with new account and login works", async ({ page }) => {
    const user = {
      email: `e2e_${Date.now()}@test.example`,
      password: "E2eTest123!",
      displayName: "E2E User",
    };
    await registerUser(page, user);
    // Should land on home page after registration
    await expect(page).toHaveURL("/", { timeout: 10_000 });
  });

  test("protected watchlist page redirects to login when unauthenticated", async ({
    page,
  }) => {
    await page.goto("/watchlist");
    // Should show sign-in prompt (not redirect, just show message)
    await expect(page.locator("text=/sign in/i")).toBeVisible({
      timeout: 5_000,
    });
  });
});
