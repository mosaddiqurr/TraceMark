const API_ROOT = import.meta.env.VITE_API_URL ?? "/api/v1";

export interface ApiErrorBody {
  code: string;
  message: string;
  field_errors?: Record<string, string[]>;
  correlation_id?: string;
}

export class ApiError extends Error {
  constructor(public status: number, public body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
  }
}

let csrfToken: string | null = null;
export function setCsrfToken(value: string | null) { csrfToken = value; }

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (csrfToken && !["GET", "HEAD", "OPTIONS"].includes((init.method ?? "GET").toUpperCase())) headers.set("X-CSRF-Token", csrfToken);
  headers.set("Accept", "application/json");
  const response = await fetch(`${API_ROOT}${path}`, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    let body: ApiErrorBody = { code: "request_failed", message: "The request could not be completed." };
    try { body = { ...body, ...(await response.json()) }; } catch { /* Non-JSON errors stay generic. */ }
    throw new ApiError(response.status, body);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const jsonBody = (value: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(value) });
