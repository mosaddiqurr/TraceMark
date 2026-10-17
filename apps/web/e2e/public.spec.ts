import { expect, test } from "@playwright/test";
import { resolve } from "node:path";
import { checkAccessibility } from "./accessibility";

test("four focused pages stay aligned at the configured viewport", async ({
  page,
}, testInfo) => {
  for (const path of ["/", "/protect", "/verify", "/about"]) {
    await page.goto(path);
    await expect(
      page.getByRole("navigation", { name: "Main navigation" }),
    ).toBeVisible();
    await expect(page.locator("h1")).toBeVisible();
    await checkAccessibility(page);
    await expect(page).toHaveTitle(/TraceMark$/);
    for (const asset of [
      "/brand/tracemark-logo.png",
      "/brand/favicon.ico",
      "/brand/apple-touch-icon.png",
    ]) {
      const response = await page.request.get(asset);
      expect(response.ok()).toBe(true);
      expect(response.headers()["content-type"]).toMatch(/^image\//);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    const box = await page.locator("main").boundingBox();
    expect(box).not.toBeNull();
    expect(
      Math.abs(box!.x * 2 + box!.width - testInfo.project.use.viewport!.width),
    ).toBeLessThan(2);
    if (testInfo.project.name === "desktop-1440" && path === "/") {
      await page.screenshot({
        path: resolve("../../docs/screenshots/desktop-1440-home.png"),
        fullPage: true,
      });
    }
  }
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await expect(
    page.getByRole("link", { name: "Use sample image" }),
  ).toBeVisible();
});
