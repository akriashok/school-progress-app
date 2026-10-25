import createClient, { type Middleware } from "openapi-fetch";
import type { components, paths } from "./api-types";

export type Schemas = components["schemas"];
export type ApiErrorBody = { error: { code: string; message: string; details?: unknown } };

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

// The access token lives in memory only; the refresh token is an httpOnly cookie.
let accessToken: string | null = null;
let onAuthLost: (() => void) | null = null;
let refreshing: Promise<boolean> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}
export function getAccessToken() {
  return accessToken;
}
export function setOnAuthLost(fn: (() => void) | null) {
  onAuthLost = fn;
}

export async function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch("/api/v1/auth/refresh", { method: "POST", credentials: "same-origin" })
      .then(async (r) => {
        if (!r.ok) {
          accessToken = null;
          return false;
        }
        const body = (await r.json()) as { access_token: string };
        accessToken = body.access_token;
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

/** fetch with the bearer token; on 401 refreshes once via the cookie and retries. */
export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const withAuth = (): RequestInit => {
    const headers = new Headers(init.headers);
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    return { ...init, headers, credentials: "same-origin" };
  };
  let res = await fetch(input, withAuth());
  if (res.status === 401 && !input.includes("/auth/")) {
    if (await refreshSession()) {
      res = await fetch(input, withAuth());
    } else {
      onAuthLost?.();
    }
  }
  return res;
}

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    if (accessToken) request.headers.set("Authorization", `Bearer ${accessToken}`);
    return request;
  },
};

export const api = createClient<paths>({
  baseUrl: "",
  credentials: "same-origin",
  fetch: async (req: Request) => {
    const res = await fetch(req.clone());
    if (res.status === 401 && !req.url.includes("/auth/")) {
      if (await refreshSession()) {
        const retry = new Request(req, { headers: new Headers(req.headers) });
        retry.headers.set("Authorization", `Bearer ${accessToken}`);
        return fetch(retry);
      }
      onAuthLost?.();
    }
    return res;
  },
});
api.use(authMiddleware);

/** Turn an openapi-fetch result into data or a thrown ApiError. */
export async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await promise;
  if (error !== undefined || !response.ok) {
    const body = error as ApiErrorBody | undefined;
    throw new ApiError(
      response.status,
      body?.error?.code ?? "HTTP_ERROR",
      body?.error?.message ?? `Request failed (${response.status})`,
      body?.error?.details,
    );
  }
  return data as T;
}

export async function errorFrom(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as ApiErrorBody;
    return new ApiError(res.status, body.error.code, body.error.message, body.error.details);
  } catch {
    return new ApiError(res.status, "HTTP_ERROR", `Request failed (${res.status})`);
  }
}

/** Download a binary endpoint (xlsx / pdf) as a file. */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const res = await authFetch(path);
  if (!res.ok) throw await errorFrom(res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function uploadFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await authFetch(path, { method: "POST", body: form });
  if (!res.ok) throw await errorFrom(res);
  return (await res.json()) as T;
}
