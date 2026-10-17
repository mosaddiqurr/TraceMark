import type { Workspace } from "./types";

const API_ROOT = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/$/, "");

export interface ApiErrorBody {
  code: string;
  message: string;
  field_errors?: Record<string, string[]>;
  correlation_id?: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: ApiErrorBody,
  ) {
    super(body.message);
    this.name = "ApiError";
  }
}

let csrfToken: string | null = null;
let workspaceRequest: Promise<Workspace> | null = null;
export function setCsrfToken(value: string | null) {
  csrfToken = value;
  if (!value) workspaceRequest = null;
}

export function ensureWorkspace(): Promise<Workspace> {
  workspaceRequest ??= api<Workspace>("/workspace", { method: "POST" })
    .then((workspace) => {
      setCsrfToken(workspace.csrf_token);
      return workspace;
    })
    .catch((error: unknown) => {
      workspaceRequest = null;
      throw error;
    });
  return workspaceRequest;
}

function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path))
    throw new Error("External API URLs are not allowed.");
  if (path.startsWith("/api/v1/")) {
    return API_ROOT.endsWith("/api/v1")
      ? `${API_ROOT}${path.slice("/api/v1".length)}`
      : path;
  }
  return `${API_ROOT}${path.startsWith("/") ? path : `/${path}`}`;
}

async function errorBody(response: Response): Promise<ApiErrorBody> {
  const fallback: ApiErrorBody = {
    code: "request_failed",
    message: "The request could not be completed.",
  };
  try {
    const value = (await response.json()) as Partial<ApiErrorBody> & {
      error?: Partial<ApiErrorBody>;
    };
    return { ...fallback, ...(value.error ?? value) };
  } catch {
    return fallback;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (
    path !== "/workspace" &&
    !["GET", "HEAD", "OPTIONS"].includes(
      (init.method ?? "GET").toUpperCase(),
    ) &&
    !csrfToken
  )
    await ensureWorkspace();
  const headers = new Headers(init.headers);
  if (
    init.body &&
    !(init.body instanceof FormData) &&
    !headers.has("Content-Type")
  )
    headers.set("Content-Type", "application/json");
  if (
    csrfToken &&
    !["GET", "HEAD", "OPTIONS"].includes((init.method ?? "GET").toUpperCase())
  )
    headers.set("X-CSRF-Token", csrfToken);
  headers.set("Accept", "application/json");
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      ...init,
      headers,
      credentials: "include",
    });
  } catch {
    throw new Error(
      "The backend service is unavailable. Check your connection and try again.",
    );
  }
  if (!response.ok) {
    throw new ApiError(response.status, await errorBody(response));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const jsonBody = (value: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(value),
});

export type ImageDownloadKind = "protected" | "distribution" | "original";

export interface ImageDownloadResult {
  filename: string;
  mediaType: string;
  size: number;
}

export class ImageDownloadError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
    this.name = "ImageDownloadError";
  }
}

const SUPPORTED_IMAGE_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
]);

function safeDownloadName(value: string | null, fallback: string): string {
  let candidate = "";
  if (value) {
    const encoded = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(value)?.[1];
    const quoted = /filename\s*=\s*"([^"]+)"/i.exec(value)?.[1];
    const plain = /filename\s*=\s*([^;]+)/i.exec(value)?.[1];
    try {
      candidate = encoded
        ? decodeURIComponent(encoded.trim())
        : (quoted ?? plain ?? "").trim();
    } catch {
      candidate = quoted ?? plain ?? "";
    }
  }
  candidate =
    candidate
      .replaceAll("\\", "/")
      .split("/")
      .at(-1)
      ?.replace(/[\p{Cc}<>:"|?*]+/gu, "_")
      .replace(/^\.+/, "")
      .trim() ?? "";
  return candidate.slice(0, 180) || fallback;
}

function downloadFailureMessage(
  kind: ImageDownloadKind,
  status: number,
): string {
  if (status === 404) {
    if (kind === "protected")
      return "The protected image is unavailable or its download window has expired. Protect the image again.";
    return "This image is unavailable in this browser workspace.";
  }
  if (status === 401)
    return "Your browser workspace has expired. Reload the page and try again.";
  if (status >= 500) return "The backend service is unavailable.";
  return kind === "protected"
    ? "The protected image could not be downloaded."
    : kind === "distribution"
      ? "The distribution copy could not be downloaded."
      : "The original image could not be downloaded.";
}

export async function loadImage(
  path: string,
  kind: ImageDownloadKind = "protected",
): Promise<{ blob: Blob; filename: string; mediaType: string }> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      credentials: "include",
      headers: { Accept: "image/png,image/jpeg,image/webp" },
    });
  } catch {
    throw new ImageDownloadError("The backend service is unavailable.");
  }

  if (!response.ok) {
    throw new ImageDownloadError(
      downloadFailureMessage(kind, response.status),
      response.status,
    );
  }

  const mediaType = (response.headers.get("Content-Type") ?? "")
    .split(";", 1)[0]
    .trim()
    .toLowerCase();
  if (!SUPPORTED_IMAGE_TYPES.has(mediaType)) {
    throw new ImageDownloadError(
      "The file response was not a valid image.",
      response.status,
    );
  }

  const blob = await response.blob();
  if (blob.size === 0)
    throw new ImageDownloadError(
      "The downloaded image was empty.",
      response.status,
    );
  if (blob.type && !SUPPORTED_IMAGE_TYPES.has(blob.type.toLowerCase())) {
    throw new ImageDownloadError(
      "The file response was not a valid image.",
      response.status,
    );
  }

  const extensions: Record<string, string> = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
  };
  const filename = safeDownloadName(
    response.headers.get("Content-Disposition"),
    `tracemark-${kind}.${extensions[mediaType]}`,
  );
  return { blob, filename, mediaType };
}

function saveBlob(blob: Blob, filename: string) {
  const objectUrl = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.hidden = true;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export async function downloadImage(
  path: string,
  kind: ImageDownloadKind,
): Promise<ImageDownloadResult> {
  const { blob, filename, mediaType } = await loadImage(path, kind);
  saveBlob(blob, filename);
  return { filename, mediaType, size: blob.size };
}

export async function downloadReport(
  path: string,
  format: "json" | "pdf",
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(apiUrl(`${path}?format=${format}`), {
      credentials: "include",
    });
  } catch {
    throw new Error("The backend service is unavailable.");
  }
  if (!response.ok)
    throw new ApiError(response.status, await errorBody(response));
  const expected = format === "json" ? "application/json" : "application/pdf";
  if (!response.headers.get("Content-Type")?.startsWith(expected))
    throw new Error("The report response was invalid.");
  const blob = await response.blob();
  if (!blob.size) throw new Error("The report response was empty.");
  saveBlob(
    blob,
    safeDownloadName(
      response.headers.get("Content-Disposition"),
      `tracemark-verification-report.${format}`,
    ),
  );
}
