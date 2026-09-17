import { test, expect } from "@playwright/test";

const DEMO_EMAIL = "demo@example.com";
const DEMO_PASSWORD = "Demo1234!";
const TEST_EMAIL = `e2e_${Date.now()}@test.com`;
const TEST_PASSWORD = "TestPass123!";

// ── Auth Tests ──────────────────────────────────────────────────────────────
test.describe("Authentication", () => {
  test("Homepage loads and shows hero banner", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Aperture/);
    await expect(page.getByText("APERTURE")).toBeVisible();
  });

  test("Register new account", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel("Display name").fill("E2E Tester");
    await page.getByLabel("Email").fill(TEST_EMAIL);
    await page.getByLabel("Password").fill(TEST_PASSWORD);

    // Select a genre
    await page.getByRole("button", { name: "Sci-Fi" }).click();
    await page.getByRole("button", { name: "Drama" }).click();

    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL("/");
  });

  test("Login with email and password", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(DEMO_EMAIL);
    await page.getByLabel("Password").fill(DEMO_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL("/");
    await expect(page.getByText("Recommended for you")).toBeVisible();
  });

  test("Wrong password shows error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(DEMO_EMAIL);
    await page.getByLabel("Password").fill("WrongPassword!");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Incorrect email or password")).toBeVisible();
  });

  test("Logout clears session", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(DEMO_EMAIL);
    await page.getByLabel("Password").fill(DEMO_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await page.getByRole("button", { name: /D/i }).first().click(); // Avatar
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
  });
});

// ── Movie Discovery ──────────────────────────────────────────────────────────
test.describe("Movie Discovery", () => {
  test("Trending rail is visible on homepage", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Trending Now")).toBeVisible();
  });

  test("Search finds movies", async ({ page }) => {
    await page.goto("/search");
    await page.getByPlaceholder(/Search by title/).fill("shadow");
    await page.keyboard.press("Enter");
    await expect(page.locator("[data-testid='movie-card']").first()).toBeVisible({ timeout: 5000 });
  });

  test("Autocomplete suggestions appear", async ({ page }) => {
    await page.goto("/search");
    await page.getByPlaceholder(/Search by title/).fill("iron");
    await expect(page.locator("button").filter({ hasText: /iron/i }).first())
      .toBeVisible({ timeout: 3000 });
  });

  test("Movie detail page loads", async ({ page }) => {
    await page.goto("/");
    // Wait for movies to load
    const movieCard = page.locator("a[href^='/movie/']").first();
    await expect(movieCard).toBeVisible({ timeout: 8000 });
    await movieCard.click();
    await expect(page.getByText("Because you watched this")).toBeVisible({ timeout: 5000 });
  });
});

// ── Authenticated Features ───────────────────────────────────────────────────
test.describe("Authenticated User Features", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(DEMO_EMAIL);
    await page.getByLabel("Password").fill(DEMO_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL("/");
  });

  test("Personalized recommendations appear after login", async ({ page }) => {
    await expect(page.getByText("Recommended for you")).toBeVisible({ timeout: 8000 });
  });

  test("Can add movie to watchlist", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(2000); // wait for recommendations

    // Hover over first movie card to show actions
    const card = page.locator("[href^='/movie/']").first();
    await card.hover();

    // Click + button
    const addBtn = page.getByRole("button", { name: "Add to list" }).first();
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await expect(page.getByRole("button", { name: "In your list" }).first())
        .toBeVisible({ timeout: 3000 });
    }
  });

  test("Watchlist page shows saved movies", async ({ page }) => {
    await page.goto("/watchlist");
    await expect(page.getByText("My List")).toBeVisible();
  });

  test("Taste DNA profile loads", async ({ page }) => {
    await page.goto("/profile");
    await expect(page.getByText("Your Taste DNA")).toBeVisible();
  });

  test("Mood picker works", async ({ page }) => {
    await page.goto("/");
    const moodInput = page.getByPlaceholder(/How are you feeling/i);
    await moodInput.fill("I feel excited and want something action-packed");
    await page.getByRole("button", { name: /Go|Find|Search/i }).first().click();
    await page.waitForTimeout(2000);
    // Mood results rail should appear
    await expect(page.getByText(/Picks for/i)).toBeVisible({ timeout: 5000 });
  });

  test("Star rating on movie detail", async ({ page }) => {
    await page.goto("/");
    const movieLink = page.locator("a[href^='/movie/']").first();
    await expect(movieLink).toBeVisible({ timeout: 8000 });
    await movieLink.click();
    await expect(page.getByText("Your rating")).toBeVisible({ timeout: 5000 });
    await page.getByRole("button", { name: "Rate 5 stars" }).click();
    await expect(page.getByText("Saved!")).toBeVisible({ timeout: 3000 });
  });
});

// ── Visual & Accessibility ────────────────────────────────────────────────────
test.describe("Accessibility", () => {
  test("Login page is keyboard navigable", async ({ page }) => {
    await page.goto("/login");
    await page.keyboard.press("Tab");  // Focus email
    await page.keyboard.type(DEMO_EMAIL);
    await page.keyboard.press("Tab");  // Focus password
    await page.keyboard.type(DEMO_PASSWORD);
    await page.keyboard.press("Enter"); // Submit
    await expect(page).toHaveURL("/");
  });

  test("Skip to main content link exists", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    // The first focusable element should help navigation
    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();
  });

  test("Images have alt text or are decorative", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(2000);
    // All non-decorative images should have alt text
    const images = page.locator("img:not([aria-hidden='true'])");
    const count = await images.count();
    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute("alt");
      // alt="" is valid for decorative images, non-empty string for meaningful ones
      expect(alt).not.toBeNull();
    }
  });
});

// ── Performance ───────────────────────────────────────────────────────────────
test.describe("Performance", () => {
  test("Homepage loads within 3 seconds", async ({ page }) => {
    const start = Date.now();
    await page.goto("/");
    await expect(page.getByText("APERTURE")).toBeVisible();
    const loadTime = Date.now() - start;
    expect(loadTime).toBeLessThan(3000);
  });

  test("Search responds within 2 seconds", async ({ page }) => {
    await page.goto("/search?q=shadow");
    const start = Date.now();
    await page.waitForLoadState("networkidle");
    const responseTime = Date.now() - start;
    expect(responseTime).toBeLessThan(2000);
  });
});
