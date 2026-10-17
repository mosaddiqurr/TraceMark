import axe from "axe-core";
import { expect, type Page } from "@playwright/test";

export async function checkAccessibility(page: Page) {
  await page.evaluate(axe.source);
  const result = await page.evaluate(async () => {
    const engine = (window as typeof window & { axe: typeof axe }).axe;
    return engine.run({
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    });
  });
  expect(
    result.violations.map(({ id, nodes }) => ({
      id,
      targets: nodes.map(({ target }) => target),
    })),
  ).toEqual([]);
}
