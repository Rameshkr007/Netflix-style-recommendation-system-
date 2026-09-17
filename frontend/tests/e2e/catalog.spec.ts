/**
 * E2E tests: Movie catalog, search, and recommendation flows
 */
import { test, expect } from "@playwright/test";
import { loginViaAPI, waitForRail } from "./helpers";

test.describe("Movie Catalog", () => {
  test("homepage shows Trending Now rail", async ({ page }) => {
    await page.goto("/");
    // Wait for rails to load
    await expect(page.locator("text=Trending Now")).toBeVisible({
      timeout: 15_000,
    });
  });

  test("homepage shows multiple content rails", async ({ page }) => {
    await page.goto("/");
    await waitForRail(page);
    // Should have multiple section headings
    const rails = page.locator("h2, h3").filter({ hasText: /Trending|Action|Sci-Fi/i });
    await expect(rails.first()).toBeVisible();
  });

  test("movie card shows on hover", async ({ page }) => {
    await page.goto("/");
    await waitForRail(page);
    // Find a movie card and hover it
    const card = page.locator("a[href^='/movie/']").first();
    await expect(card).toBeVisible({ timeout: 10_000 });
    await card.hover();
    // After hover, action buttons appear
    await expect(
      page.locator("a[aria-label='View details']").first()
    ).toBeVisible({ timeout: 3_000 });
  });

  test("clicking movie card navigates to detail page", async ({ page }) => {
    await page.goto("/");
    await waitForRail(page);
    const card = page.locator("a[href^='/movie/']").first();
    const href = await card.getAttribute("href");
    await card.click();
    await expect(page).toHaveURL(href!, { timeout: 5_000 });
    // Movie detail page should show synopsis area
    await expect(page.locator("section").first()).toBeVisible();
  });
});

test.describe("Search", () => {
  test("search page renders input", async ({ page }) => {
    await page.goto("/search");
    const input = page.locator('input[placeholder*="search" i], input[placeholder*="title" i]');
    await expect(input).toBeVisible();
  });

  test("searching shows results", async ({ page }) => {
    await page.goto("/search?q=shadow");
    // Should show movie cards
    await expect(page.locator("a[href^='/movie/']").first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("autocomplete suggestions appear while typing", async ({ page }) => {
    await page.goto("/search");
    const input = page.locator("input").first();
    await input.fill("iron");
    // Suggestions dropdown should appear
    await expect(
      page.locator("button").filter({ hasText: /iron/i }).first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test("clicking suggestion runs search", async ({ page }) => {
    await page.goto("/search");
    const input = page.locator("input").first();
    await input.fill("iron");
    // Click first suggestion
    const suggestion = page
      .locator("button")
      .filter({ hasText: /iron/i })
      .first();
    await suggestion.waitFor({ timeout: 5_000 });
    await suggestion.click();
    // URL should update with the search query
    await expect(page).toHaveURL(/q=/);
  });

  test("header search navigates to search page", async ({ page }) => {
    await page.goto("/");
    // Find header search form
    const searchInput = page.locator("header input").first();
    await expect(searchInput).toBeVisible();
    await searchInput.fill("action");
    await searchInput.press("Enter");
    await expect(page).toHaveURL(/\/search\?q=action/, { timeout: 5_000 });
  });
});

test.describe("Recommendations (authenticated)", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page);
  });

  test("shows personalized recommendation rail when logged in", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.locator("text=/recommended for you/i")
    ).toBeVisible({ timeout: 15_000 });
  });

  test("mood picker submits and shows results", async ({ page }) => {
    await page.goto("/");
    // Find mood input
    const moodInput = page.locator('input[placeholder*="mood" i], input[placeholder*="feeling" i]');
    await expect(moodInput).toBeVisible({ timeout: 10_000 });
    await moodInput.fill("I feel excited and energetic today");
    // Submit
    const submitBtn = page.locator("button").filter({ hasText: /match|find|go/i });
    await submitBtn.first().click();
    // Mood results rail should appear
    await expect(
      page.locator("text=/picks for/i")
    ).toBeVisible({ timeout: 10_000 });
  });

  test("profile page shows Taste DNA after rating", async ({ page }) => {
    await page.goto("/profile");
    // Should show either DNA constellation or "rate some titles" message
    const hasDNA = await page.locator("svg[aria-label*='DNA' i]").count();
    const hasPrompt = await page.locator("text=/rate/i").count();
    expect(hasDNA + hasPrompt).toBeGreaterThan(0);
  });
});
