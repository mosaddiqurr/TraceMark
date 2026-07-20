import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import axe from "axe-core";
import { App } from "./App";
import { renderApp } from "./test/render";

const signedOut = () => vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ code: "unauthenticated", message: "Authentication required" }), { status: 401, headers: { "Content-Type": "application/json" } }));

describe("TraceMark application", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("presents the evidence-led landing page", async () => {
    signedOut();
    renderApp(<App />);
    expect(screen.getByRole("heading", { name: /leave a mark/i })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("link", { name: /create workspace/i })).toBeInTheDocument());
  });

  it("redirects a signed-out workspace request to sign in", async () => {
    signedOut();
    renderApp(<App />, ["/app"]);
    expect(await screen.findByRole("heading", { name: /sign in to tracemark/i })).toBeInTheDocument();
  });

  it("submits credentials through the session API", async () => {
    const fetchMock = signedOut();
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ code: "unauthenticated", message: "Authentication required" }), { status: 401, headers: { "Content-Type": "application/json" } }));
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ user: { id: "user-1", email: "analyst@example.test", display_name: "Analyst", role: "user" }, csrf_token: "csrf" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ asset_count: 0, protected_count: 0, collection_count: 0, active_job_count: 0, recent_jobs: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    renderApp(<App />, ["/login"]);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/email address/i), "analyst@example.test");
    await user.type(screen.getByLabelText(/^password/i), "correct horse battery staple");
    await user.click(screen.getByRole("button", { name: /^sign in/i }));
    expect(await screen.findByRole("heading", { name: /evidence overview/i })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/login", expect.objectContaining({ credentials: "include", method: "POST" }));
  });

  it("has no automatically detectable critical accessibility violations on the landing page", async () => {
    signedOut();
    const { container } = renderApp(<App />);
    await screen.findByRole("link", { name: /create workspace/i });
    const results = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    expect(results.violations.filter((violation) => violation.impact === "critical")).toEqual([]);
  });
});
