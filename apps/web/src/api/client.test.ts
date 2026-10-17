import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, downloadImage, setCsrfToken } from "./client";

describe("API client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setCsrfToken(null);
  });

  it("preserves the safe structured API error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "invalid_image",
            message: "The image could not be decoded.",
            correlation_id: "req-123",
          },
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );
    await expect(api("/verification")).rejects.toMatchObject({
      status: 422,
      body: { code: "invalid_image", correlation_id: "req-123" },
    });
  });

  it("sends cookies and CSRF on mutations", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));
    setCsrfToken("csrf-value");
    await api("/workspace", { method: "DELETE" });
    const init = fetchMock.mock.calls[0][1];
    expect(init?.credentials).toBe("include");
    expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("csrf-value");
  });

  it("downloads authenticated image bytes with a safe server filename", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(new Blob(["image-payload"], { type: "image/png" }), {
        status: 200,
        headers: {
          "Content-Type": "image/png",
          "Content-Disposition": 'attachment; filename="../../protected.png"',
        },
      }),
    );
    const createObjectURL = vi.fn(() => "blob:tracemark");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    await expect(
      downloadImage("/api/v1/outputs/output-1/download", "protected"),
    ).resolves.toEqual({
      filename: "protected.png",
      mediaType: "image/png",
      size: 13,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/outputs/output-1/download",
      expect.objectContaining({
        credentials: "include",
      }),
    );
    expect(click).toHaveBeenCalledOnce();
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:tracemark");
  });

  it("does not save JSON or owner-scoped missing-record responses as images", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            error: { code: "not_found", message: "protected output not found" },
          }),
          { status: 404, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    await expect(
      downloadImage("/api/v1/outputs/missing/download", "protected"),
    ).rejects.toThrow(
      "The protected image is unavailable or its download window has expired. Protect the image again.",
    );
    await expect(
      downloadImage("/api/v1/outputs/not-an-image/download", "protected"),
    ).rejects.toThrow("The file response was not a valid image.");
    expect(click).not.toHaveBeenCalled();
  });
});
