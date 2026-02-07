import { expect, test } from "@playwright/test";

test("known flow builds a Mode B subscription URL", async ({ page }) => {
  await page.route("**/version", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        service_version: "0.1.0",
        schema_version: 1,
        meta: { generated_at: "2026-01-01T00:00:00" },
      }),
    });
  });

  await page.route("**/debug**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        mode: "bypass",
        days: 365,
        types: ["trash", "recycling"],
        events: [{ date: "2026-02-12", types: ["trash", "recycling"] }],
      }),
    });
  });

  await page.goto("/");
  await page.getByRole("link", { name: "Open town page" }).first().click();
  await page.getByRole("button", { name: "Generate preview and URL" }).click();

  await expect(page.getByText("Your subscription URL")).toBeVisible();
  const urlText = await page.locator("p.break-all").innerText();
  expect(urlText).toContain("/town.ics?weekday=");
  expect(urlText).not.toContain("address=");
});
