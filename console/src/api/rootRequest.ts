import { getRootApiUrl } from "./config.ts";
import { buildHttpError } from "./errors.ts";

export interface RootRequestOptions extends RequestInit {
  allowedStatuses?: number[];
}

export async function rootRequest<T = unknown>(
  path: string,
  options: RootRequestOptions = {},
): Promise<T> {
  const { allowedStatuses, ...fetchOptions } = options;
  const response = await fetch(getRootApiUrl(path), fetchOptions);

  if (!response.ok && !allowedStatuses?.includes(response.status)) {
    const text = await response.text().catch(() => "");
    const contentType = response.headers.get("content-type") || "";
    throw buildHttpError(response.status, response.statusText, text, contentType);
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return (await response.text()) as T;
  }
  return response.json();
}
