import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const TOKEN_KEY = "agentic_rag_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Transient-failure retry.
 *
 * The backend can take ~25–30s to finish booting (RAG init + DB connect), and
 * during that window the dev proxy / server may answer with a plain 5xx or a
 * dropped connection. That surfaces to the user as an intermittent
 * "Request failed with status code 500" on login that succeeds on the next try.
 * We retry those transient cases automatically so the first attempt just works.
 *
 * Only retried when it is safe to do so: network errors and 5xx responses, on
 * idempotent requests (GET) and the auth endpoints (login/guest/logout are
 * find-or-create / stateless, so replaying them has no harmful side effect).
 * 4xx responses (401/403/404/422) are never retried — those are real answers.
 */
const MAX_RETRIES = 2;
const RETRY_BASE_MS = 600;

const RETRYABLE_POST_PATHS = ["/auth/login", "/auth/guest", "/auth/logout"];

function isRetryable(error: AxiosError): boolean {
  const config = error.config as (InternalAxiosRequestConfig & { _retryCount?: number }) | undefined;
  if (!config) return false;

  const method = (config.method || "get").toLowerCase();
  const url = config.url || "";
  const safeMethod = method === "get";
  const safeAuthPost = method === "post" && RETRYABLE_POST_PATHS.some((p) => url.includes(p));
  if (!safeMethod && !safeAuthPost) return false;

  // No response → network error / connection reset / proxy failure while booting.
  if (!error.response) return true;
  // Server-side transient (500/502/503/504). Client 4xx are real answers, not transient.
  return error.response.status >= 500;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as (InternalAxiosRequestConfig & { _retryCount?: number }) | undefined;

    if (config && isRetryable(error)) {
      config._retryCount = (config._retryCount ?? 0) + 1;
      if (config._retryCount <= MAX_RETRIES) {
        const backoff = RETRY_BASE_MS * 2 ** (config._retryCount - 1);
        const jitter = Math.random() * 200;
        await new Promise((resolve) => setTimeout(resolve, backoff + jitter));
        return api(config);
      }
    }

    if (error.response?.status === 401 && window.location.pathname !== "/login") {
      setToken(null);
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);
