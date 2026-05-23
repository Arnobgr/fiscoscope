import { test, expect } from "@playwright/test";

test("overview loads and a card opens its detail", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Efficacité administrative")).toBeVisible();
  await page.getByRole("link", { name: /Coût administratif/ }).click();
  await expect(page).toHaveURL(/\/kpi\/overhead_rate/);
  await expect(page.getByRole("heading", { name: /Coût administratif/ })).toBeVisible();
});
