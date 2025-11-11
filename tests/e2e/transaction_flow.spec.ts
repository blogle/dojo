import { expect, test } from "@playwright/test";

test.describe("Transaction Flow", () => {
  test("shows validation errors for missing amount", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('select[name="account_id"] option');

    await page.fill('input[name="amount"]', "");
    await page.click('button[type="submit"]');

    await expect(page.locator('[data-error-for="amount_minor"]')).toHaveText("Enter a numeric amount.");
  });

  test("records a transaction and updates net worth", async ({ page, request }) => {
    await page.goto("/");
    await page.waitForSelector('select[name="account_id"] option');

    const baseURL = test.info().project.use.baseURL ?? "http://127.0.0.1:8765";
    const initialResponse = await request.get(`${baseURL}/api/net-worth/current`);
    const initialSnapshot = await initialResponse.json();
    const initialNetWorth = initialSnapshot.net_worth_minor as number;

    const amountDollars = 12.34;
    const amountMinor = -Math.round(amountDollars * 100);

    await page.selectOption('select[name="account_id"]', { value: "house_checking" });
    await page.selectOption('select[name="category_id"]', { value: "groceries" });
    await page.fill('input[name="amount"]', amountDollars.toString());
    await page.selectOption('select[name="flow_direction"]', { value: "expense" });
    await page.fill('input[name="memo"]', "Playwright test");
    await page.click('button[type="submit"]');

    await expect(page.locator("#submission-status")).toHaveText("Transaction recorded.");

    await expect
      .poll(async () => {
        const updatedResponse = await request.get(`${baseURL}/api/net-worth/current`);
        const updatedSnapshot = await updatedResponse.json();
        return updatedSnapshot.net_worth_minor as number;
      })
      .toBe(initialNetWorth + amountMinor);
  });
});
