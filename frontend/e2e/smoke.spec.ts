import { test, expect } from "@playwright/test";

test("overview loads and a card opens its detail", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Efficacité administrative")).toBeVisible();
  await page.getByRole("link", { name: /Part de la masse salariale publique/ }).click();
  await expect(page).toHaveURL(/\/kpi\/overhead_rate/);
  await expect(page.getByRole("heading", { name: /Part de la masse salariale publique/ })).toBeVisible();
});
