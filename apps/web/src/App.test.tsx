import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import axe from "axe-core";
import { App } from "./App";
import { setCsrfToken } from "./api/client";
import { renderApp } from "./test/render";

describe("TraceMark application", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setCsrfToken(null);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          csrf_token: "test-csrf",
          expires_at: "2026-11-01",
          limits: {
            max_upload_bytes: 20971520,
            max_image_pixels: 4000000,
            max_image_dimension: 4096,
            output_ttl_seconds: 900,
            retention_seconds: 2592000,
          },
        }),
        { headers: { "Content-Type": "application/json" } },
      ),
    );
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:test"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
  });

  it("presents the focused journey with exactly four navigation destinations", () => {
    renderApp(<App />);
    expect(
      screen.getByRole("heading", { name: /protect the image/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /protect an image/i }),
    ).toHaveAttribute("href", "/protect");
    expect(
      screen.getByRole("link", { name: /verify an image/i }),
    ).toHaveAttribute("href", "/verify");
    expect(screen.getByRole("navigation")).toHaveTextContent(
      "HomeProtectVerifyAbout",
    );
    expect(screen.queryByText(/sign in/i)).not.toBeInTheDocument();
  });

  it("offers protection directly without login and validates unsupported files", async () => {
    renderApp(<App />, ["/protect"]);
    expect(
      screen.getByRole("heading", { name: /protect an image/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^protect image$/i }),
    ).toBeDisabled();
    const user = userEvent.setup({ applyAccept: false });
    await user.upload(
      screen.getByLabelText("Choose image"),
      new File(["hello"], "file.txt", { type: "text/plain" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /JPEG, PNG or WebP/i,
    );
    expect(
      screen.getByRole("button", { name: /^protect image$/i }),
    ).toBeDisabled();
  });

  it("shows a readable backend failure during automatic verification", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("Failed to fetch"),
    );
    renderApp(<App />, ["/verify"]);
    await userEvent
      .setup()
      .upload(
        screen.getByLabelText("Choose image"),
        new File(["sample"], "image.png", { type: "image/png" }),
      );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /backend service is unavailable/i,
    );
    expect(
      screen.getByRole("button", { name: /retry verification/i }),
    ).toBeEnabled();
  });

  it("explains privacy, integrity and honest limitations", () => {
    renderApp(<App />, ["/about"]);
    expect(
      screen.getByRole("heading", { name: /privacy and security/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/legal ownership, who shared/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/opaque HttpOnly browser cookie/i),
    ).toBeInTheDocument();
  });

  it("has no automatically detectable serious or critical accessibility violations", async () => {
    const { container } = renderApp(<App />);
    const results = await axe.run(container, {
      rules: { "color-contrast": { enabled: false } },
    });
    expect(
      results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious",
      ),
    ).toEqual([]);
  });
});
