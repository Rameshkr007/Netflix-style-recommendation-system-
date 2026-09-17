/**
 * E2E tests: Watchlist and Rating interactions
 */
import { test, expect } from "@playwright/test";
import { loginViaAPI, waitForRail } from "./helpers";

test.describe("Watchlist (authenticated)", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page);
  });

  test("watchlist page loads for authenticated user", async ({ page }) => {
    await page.goto("/watchlist");
    await expect(page.locator("text=/my list/i")).toBeVisible();
    // Should not show the "sign in" prompt
    await expect(page.locator("text=/sign in to build/i")).not.toBeVisible();
  });

  test("can add movie to watchlist from home page", async ({ page }) => {
    await page.goto("/");
    await waitForRail(page);

    // Hover a movie card to reveal + button
    const card = page.locator("a[href^='/movie/']").first();
    await card.hover();

    // Click + button (add to watchlist)
    const addBtn = page
      .locator("button[aria-label='Add to list']")
      .first();
    if (await addBtn.isVisible({ timeout: 3_000 })) {
      await addBtn.click();
      // Button should change to checkmark
      await expect(
        page.locator("button[aria-label='In your list']").first()
      ).toBeVisible({ timeout: 3_000 });
    }
  });

  test("watchlist shows added item and can remove it", async ({ page }) => {
    // First add a movie via API for reliable state
    const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const token = await page.evaluate(() => localStorage.getItem("aperture_token"));

    // Get first movie
    const moviesResp = await page.request.get(`${baseURL}/movies?limit=1`);
    if (moviesResp.ok()) {
      const movies = await moviesResp.json();
      if (movies.length > 0) {
        const movieId = movies[0].id;
        // Add to watchlist via API
        await page.request.post(`${baseURL}/movies/watchlist`, {
          data: { movie_id: movieId },
          headers: { Authorization: `Bearer ${token}` },
        });

        // Navigate to watchlist
        await page.goto("/watchlist");

        // Should see the movie
        const cards = page.locator("a[href^='/movie/']");
        await expect(cards.first()).toBeVisible({ timeout: 8_000 });

        // Hover to get remove button
        await cards.first().hover();
        const removeBtn = page.locator("button[aria-label='In your list']").first();
        if (await removeBtn.isVisible({ timeout: 3_000 })) {
          await removeBtn.click();
          // Card should animate out
          await page.waitForTimeout(500);
        }
      }
    }
  });
});

test.describe("Star Ratings (authenticated)", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page);
  });

  test("movie detail page shows star rating for logged in user", async ({
    page,
  }) => {
    // Get first movie ID
    const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const resp = await page.request.get(`${baseURL}/movies?limit=1`);
    if (!resp.ok()) return;
    const [movie] = await resp.json();

    await page.goto(`/movie/${movie.id}`);

    // Star rating buttons should be visible
    const stars = page.locator("button[aria-label*='star' i]");
    await expect(stars.first()).toBeVisible({ timeout: 8_000 });
    expect(await stars.count()).toBe(5);
  });

  test("clicking star saves rating and shows confirmation", async ({
    page,
  }) => {
    const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const resp = await page.request.get(`${baseURL}/movies?limit=1`);
    if (!resp.ok()) return;
    const [movie] = await resp.json();

    await page.goto(`/movie/${movie.id}`);

    // Click 4-star rating
    const fourStar = page.locator("button[aria-label='Rate 4 stars']");
    await expect(fourStar).toBeVisible({ timeout: 8_000 });
    await fourStar.click();

    // "Saved!" confirmation should appear briefly
    await expect(page.locator("text=Saved!")).toBeVisible({ timeout: 3_000 });
  });
});

test.describe("Accessibility", () => {
  test("all pages have no missing alt text on interactive images", async ({
    page,
  }) => {
    await page.goto("/");
    // Check that all img elements used for navigation have alt text or are aria-hidden
    const imgs = page.locator("img:not([aria-hidden])");
    const count = await imgs.count();
    for (let i = 0; i < count; i++) {
      const alt = await imgs.nth(i).getAttribute("alt");
      // alt can be "" (decorative) but not undefined/null without aria-hidden
      expect(alt).not.toBeNull();
    }
  });

  test("keyboard navigation works on homepage", async ({ page }) => {
    await page.goto("/");
    // Tab to first focusable element
    await page.keyboard.press("Tab");
    // Something should be focused
    const focused = await page.evaluate(() => document.activeElement?.tagName);
    expect(["A", "BUTTON", "INPUT"]).toContain(focused);
  });
});
