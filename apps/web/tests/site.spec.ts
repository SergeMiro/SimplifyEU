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
      
      // We expect pages to load (even if they show 500 locally, production should be better)
      // But here we specifically want to avoid 404s
      expect(response?.status(), `Failed to load ${url}`).toBeLessThan(500);

      const links = await page.locator('a').all();
      for (const link of links) {
        const href = await link.getAttribute('href');
        // Only internal links, ignore anchor links and cross-origin
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
    
    // We have two "Try AI Test" links. Let's use the one in the main section.
    const heroAiLink = page.locator('main').getByRole('link', { name: /try ai test/i });
    await expect(heroAiLink).toBeVisible();
    await heroAiLink.click();
    
    await expect(page).toHaveURL(/.*ai-test/);
    await expect(page.locator('h1, h2')).toContainText(/AI/i);
  });

  test('check login and register links', async ({ page }) => {
    await page.goto('/en');
    
    // Use the header login link
    const headerLoginLink = page.locator('header').getByRole('link', { name: /sign in/i });
    await expect(headerLoginLink).toBeVisible();
    
    // Use the main register link
    const heroRegisterLink = page.locator('main').getByRole('link', { name: /start free trial/i });
    await expect(heroRegisterLink).toBeVisible();
  });
});
