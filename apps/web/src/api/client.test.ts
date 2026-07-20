import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, setCsrfToken } from "./client";

describe("API client", () => {
  beforeEach(() => { vi.restoreAllMocks(); setCsrfToken(null); });

  it("preserves the safe structured API error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ code: "invalid_image", message: "The image could not be decoded.", correlation_id: "req-123" }), { status: 422, headers: { "Content-Type": "application/json" } }));
    await expect(api("/assets")).rejects.toMatchObject({ status: 422, body: { code: "invalid_image", correlation_id: "req-123" } });
  });

  it("sends cookies and CSRF on mutations", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    setCsrfToken("csrf-value");
    await api("/auth/session", { method: "DELETE" });
    const init = fetchMock.mock.calls[0][1];
    expect(init?.credentials).toBe("include");
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });
});
