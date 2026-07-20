import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/session", (route) => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ code: "unauthenticated", message: "Authentication required" }) }));
});

test("public introduction explains the product without unsupported claims", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /leave a mark/i })).toBeVisible();
  await expect(page.getByText(/evidence—not legal proof/i)).toBeVisible();
  await page.getByRole("link", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: /sign in to tracemark/i })).toBeVisible();
});

test("mobile landing page exposes the primary account action", async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes("mobile"), "Mobile-only assertion");
  await page.goto("/");
  await expect(page.getByRole("link", { name: /create workspace/i })).toBeVisible();
});
