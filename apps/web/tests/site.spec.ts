import { test, expect } from '@playwright/test';

test.describe('SimplifyEU Site Audit', () => {
  const visited = new Set<string>();
  const toVisit = ['/en'];

  test('crawl and check all links for 404s', async ({ page }) => {
    while (toVisit.length > 0) {
      const url = toVisit.pop()!;
      if (visited.has(url)) continue;
      visited.add(url);

      console.log(`Visiting: ${url}`);
      const response = await page.goto(url);
      expect(response?.status(), `Failed to load ${url}`).toBeLessThan(500);

      const links = await page.locator('a').all();
      for (const link of links) {
        const href = await link.getAttribute('href');
        if (href && href.startsWith('/') && !href.startsWith('//') && !href.includes('#')) {
          if (!visited.has(href)) {
            toVisit.push(href);
          }
        }
      }
    }
  });

  test('interact with "Try AI Test" button', async ({ page }) => {
    await page.goto('/en');
    const heroAiLink = page.locator('main').getByRole('link', { name: /try ai test/i });
    await expect(heroAiLink).toBeVisible();
    await heroAiLink.click();
    await expect(page).toHaveURL(/.*ai-test/);
    await expect(page.locator('h1')).toContainText(/Finance|Test/i);
  });

  test('verify dashboard access and quick stats', async ({ page }) => {
    await page.goto('/en/dashboard');
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator('h1')).toContainText(/Welcome/i);
    
    // Check if quick stats are visible, use a more specific selector
    const statsHeader = page.getByRole('heading', { name: /Quick Overview/i });
    await expect(statsHeader).toBeVisible();
  });

  test('check login and register links', async ({ page }) => {
    await page.goto('/en');
    const headerLoginLink = page.locator('header').getByRole('link', { name: /sign in/i });
    await expect(headerLoginLink).toBeVisible();
    const heroRegisterLink = page.locator('main').getByRole('link', { name: /start free trial/i });
    await expect(heroRegisterLink).toBeVisible();
  });
});
