declare const VITE_API_BASE_URL: string;

import { routerBasename, webchatPath } from "../utils/deployment";
import { appendCsrfHeader } from "./csrf";
import { buildHttpError } from "./errors";

function normalizeApiBaseUrl(value: string | undefined): string {
  const raw = (value || "").trim().replace(/\/+$/, "");
  return raw === "/" ? "" : raw;
}

export function getApiBaseUrl(): string {
  const base = normalizeApiBaseUrl(
    typeof VITE_API_BASE_URL === "string" ? VITE_API_BASE_URL : "",
  ) || routerBasename;
  return `${base}/api`;
}

export function getApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath}`;
}

export function getAbsoluteApiUrl(path: string): string {
  return new URL(getApiUrl(path), window.location.origin).toString();
}

export function getApiToken(): string | null {
  return localStorage.getItem("webchat_token");
}

export function setAuthToken(token: string): void {
  localStorage.setItem("webchat_token", token);
}

export function clearAuthToken(): void {
  localStorage.removeItem("webchat_token");
  localStorage.removeItem("webchat_user_id");
  localStorage.removeItem("webchat_username");
  localStorage.removeItem("webchat_agent_id");
}

export function getAuthHeaders(): Record<string, string> {
  const headers = new Headers();
  const token = getApiToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  appendCsrfHeader(headers);
  return Object.fromEntries(headers.entries()) as Record<string, string>;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = getApiUrl(path);
  const headers = new Headers(options.headers);
  const isFormData = options.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  for (const [key, value] of Object.entries(getAuthHeaders())) {
    if (!headers.has(key)) headers.set(key, value);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearAuthToken();
      const loginPath = webchatPath("/login");
      if (window.location.pathname !== loginPath) {
        window.location.href = loginPath;
      }
      throw new Error("Not authenticated");
    }
    const text = await response.text().catch(() => "");
    const contentType = response.headers.get("content-type") || "";
    throw buildHttpError(response.status, response.statusText, text, contentType);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return (await response.text()) as T;
  }

  return response.json();
}
