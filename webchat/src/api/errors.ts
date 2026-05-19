export class ApiRequestError extends Error {
  status: number;
  statusText: string;
  bodyText: string;

  constructor(status: number, statusText: string, message: string, bodyText = "") {
    super(message || `Request failed: ${status} ${statusText}`);
    this.name = "ApiRequestError";
    this.status = status;
    this.statusText = statusText;
    this.bodyText = bodyText;
  }
}

export function extractErrorMessage(
  text: string,
  contentType: string,
): string | null {
  if (!text) return null;
  if (!contentType.includes("application/json")) return text;

  try {
    const payload = JSON.parse(text) as {
      detail?: unknown;
      message?: unknown;
      error?: unknown;
    };
    if (typeof payload.detail === "string" && payload.detail) return payload.detail;
    if (typeof payload.message === "string" && payload.message) return payload.message;
    if (typeof payload.error === "string" && payload.error) return payload.error;
  } catch {
    return text;
  }
  return text;
}

export function buildHttpError(
  status: number,
  statusText: string,
  bodyText: string,
  contentType: string,
): ApiRequestError {
  return new ApiRequestError(
    status,
    statusText,
    extractErrorMessage(bodyText, contentType) || "",
    bodyText,
  );
}
