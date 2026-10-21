import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { checkAccessibility } from "./accessibility";

test("real image journey: protect, download, re-upload, evidence and reports", async ({
  page,
}, testInfo) => {
  // Five real image operations each have a separate bounded backend deadline.
  test.setTimeout(240_000);
  await page.goto("/");
  await page.getByRole("link", { name: "Use sample image" }).click();
  await expect(
    page.getByText("tracemark-sample.png", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Recipient or reference").fill("Portfolio review");
  await page
    .getByRole("button", { name: "Protect image", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Image protected" }),
  ).toBeVisible({ timeout: 45_000 });
  const identifier = await page.locator(".identifier code").textContent();
  await checkAccessibility(page);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download protected image" }).click();
  const download = await downloadPromise;
  const filename = testInfo.outputPath("protected.png");
  await download.saveAs(filename);
  const content = await readFile(filename);
  expect(content.subarray(0, 8)).toEqual(
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
  );
  expect(content.length).toBeGreaterThan(1000);
  if (testInfo.project.name === "desktop-1440")
    await page.screenshot({
      path: resolve(
        "../../docs/screenshots",
        `${testInfo.project.name}-protected.png`,
      ),
      fullPage: true,
    });
  await page.getByRole("button", { name: "Protect another image" }).click();
  await expect(page.getByLabel("Recipient or reference")).toHaveValue("");
  await expect(
    page.getByRole("button", { name: "Protect image", exact: true }),
  ).toBeDisabled();
  await page.getByRole("link", { name: "Verify", exact: true }).click();
  await page.reload();
  await page.getByLabel("Choose image").setInputFiles(filename);
  await expect(
    page.getByRole("heading", { name: "VERIFIED", exact: true }),
  ).toBeVisible({ timeout: 45_000 });
  await expect(page.locator(".identifier code")).toHaveText(identifier!);
  await expect(
    page.getByText("Portfolio review", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Protected copy matches", { exact: true }),
  ).toBeVisible();
  await page.getByText("View detailed evidence").click();
  await checkAccessibility(page);
  await expect(
    page.getByText(createHash("sha256").update(content).digest("hex"), {
      exact: true,
    }),
  ).toBeVisible();
  if (["desktop-1440", "mobile-390"].includes(testInfo.project.name))
    await page.screenshot({
      path: resolve(
        "../../docs/screenshots",
        `${testInfo.project.name}-verified.png`,
      ),
      fullPage: true,
    });
  for (const format of ["PDF", "JSON"]) {
    const exporting = page.waitForEvent("download");
    await page.getByRole("button", { name: `Export ${format}` }).click();
    const report = await exporting;
    const path = testInfo.outputPath(`report.${format.toLowerCase()}`);
    await report.saveAs(path);
    const bytes = await readFile(path);
    if (format === "PDF") expect(bytes.subarray(0, 4).toString()).toBe("%PDF");
    else {
      const evidence = JSON.parse(bytes.toString());
      expect(evidence.verified).toBe(true);
      expect(evidence.identifier).toBe(identifier);
      expect(evidence.authentication.scheme).toBe("HMAC-SHA256");
    }
  }
  await page.getByLabel("Choose image").setInputFiles({
    name: "unsupported.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("invalid"),
  });
  await expect(page.getByRole("alert")).toContainText("JPEG, PNG or WebP");
  await expect(
    page.getByRole("heading", { name: "VERIFIED", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "Protect", exact: true }).click();
  await page.getByLabel("Choose image").setInputFiles(filename);
  await page
    .getByRole("button", { name: "Protect image", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Image protected" }),
  ).toBeVisible({ timeout: 45_000 });
  await page.getByRole("button", { name: "Verify this image" }).click();
  await expect(
    page.getByRole("heading", { name: "VERIFIED", exact: true }),
  ).toBeVisible({ timeout: 45_000 });
  await page.getByRole("link", { name: "About", exact: true }).click();
  await page
    .getByRole("button", { name: "Clear this browser's traces" })
    .click();
  await page
    .getByRole("button", { name: "Clear private traces", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("cleared");
  await page.getByRole("link", { name: "Verify", exact: true }).click();
  await page.getByLabel("Choose image").setInputFiles(filename);
  await expect(
    page.getByRole("heading", { name: "NOT VERIFIED", exact: true }),
  ).toBeVisible({ timeout: 45_000 });
  await expect(page.getByText("Portfolio review", { exact: true })).toHaveCount(
    0,
  );
  await expect(
    page.getByText(/An authentic watermark was recovered/),
  ).toBeVisible();
});

test("invalid, oversized, corrupt, unmarked and unavailable backend states are honest", async ({
  page,
}) => {
  await page.goto("/verify");
  const input = page.getByLabel("Choose image");
  await input.setInputFiles({
    name: "invalid.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("invalid"),
  });
  await expect(page.getByRole("alert")).toContainText("JPEG, PNG or WebP");
  await input.setInputFiles({
    name: "large.png",
    mimeType: "image/png",
    buffer: Buffer.alloc(21 * 1024 * 1024),
  });
  await expect(page.getByRole("alert")).toContainText("smaller than");
  await input.setInputFiles({
    name: "corrupt.png",
    mimeType: "image/png",
    buffer: Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 0]),
  });
  await expect(page.getByRole("alert")).toContainText("decoded safely", {
    timeout: 45_000,
  });
  const sample = await readFile(resolve("public/sample.png"));
  await input.setInputFiles({
    name: "unmarked.png",
    mimeType: "image/png",
    buffer: sample,
  });
  await expect(
    page.getByRole("heading", { name: "NOT VERIFIED", exact: true }),
  ).toBeVisible({ timeout: 45_000 });
  await page.route("**/api/v1/verification", (route) => route.abort("failed"));
  await input.setInputFiles({
    name: "offline.png",
    mimeType: "image/png",
    buffer: sample,
  });
  await expect(page.getByRole("alert")).toContainText(
    "backend service is unavailable",
  );
  await expect(
    page.getByRole("heading", { name: "VERIFIED", exact: true }),
  ).toHaveCount(0);
});

test("link checks refuse private addresses and trace records round-trip", async ({
  page,
}, testInfo) => {
  test.setTimeout(120_000);
  await page.goto("/verify");
  await page
    .getByLabel("Image or page link")
    .fill("http://127.0.0.1/private.png");
  await page.getByRole("button", { name: "Check link" }).click();
  await expect(page.getByRole("alert")).toContainText("non-public");
  await expect(
    page.getByRole("link", { name: "TinEye" }).first(),
  ).toHaveAttribute("rel", "noopener noreferrer");
  await checkAccessibility(page);

  await page.goto("/protect?sample=1");
  await expect(
    page.getByText("tracemark-sample.png", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Protect image", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Image protected" }),
  ).toBeVisible({ timeout: 45_000 });

  await page.goto("/about");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Save trace records" }).click();
  const download = await downloadPromise;
  const records = testInfo.outputPath("trace-records.json");
  await download.saveAs(records);
  const exported = JSON.parse(await readFile(records, "utf8")) as {
    kind: string;
    traces: unknown[];
  };
  expect(exported.kind).toBe("tracemark-trace-export");
  expect(exported.traces.length).toBeGreaterThan(0);
  await page
    .getByLabel("Restore trace records from file")
    .setInputFiles(records);
  await expect(page.getByRole("status")).toContainText("already here");
  await checkAccessibility(page);
});
